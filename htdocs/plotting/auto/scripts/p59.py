"""u and v wind climatology"""
import datetime
import calendar

import numpy as np
import pandas as pd
from pandas.io.sql import read_sql
from pyiem.plot.use_agg import plt
from pyiem.util import get_autoplot_context, get_dbconn
from pyiem.exceptions import NoDataFound
from metpy.units import units
from metpy.calc import wind_components

PDICT = {
    "mps": "Meters per Second",
    "kt": "Knots",
    "kmh": "Kilometers per Hour",
    "mph": "Miles per Hour",
}
XREF_UNITS = {
    "mps": units("meter / second"),
    "kt": units("knot"),
    "kmh": units("kilometer / hour"),
    "mph": units("mile / hour"),
}


def smooth(x):
    """Smooth the data"""
    return pd.Series(x).rolling(7, min_periods=1).mean()


def get_description():
    """Return a dict describing how to call this plotter"""
    desc = dict()
    desc["data"] = True
    desc["cache"] = 86400
    desc[
        "description"
    ] = """This plot presents a climatology of wind
    observations.  The top panel presents the u (east/west) and v (north/south)
    components.  The bottom panel is the simple average of the wind speed
    magnitude.  The plotted information contains a seven day smoother.  If you
    download the raw data, it will not contain this smoothing."""
    desc["arguments"] = [
        dict(
            type="zstation",
            name="station",
            default="DSM",
            network="IA_ASOS",
            label="Select Station:",
        ),
        dict(
            type="select",
            name="units",
            default="mph",
            label="Wind Speed Units:",
            options=PDICT,
        ),
    ]
    return desc


def plotter(fdict):
    """Go"""
    asos = get_dbconn("asos")

    ctx = get_autoplot_context(fdict, get_description())
    station = ctx["station"]
    plot_units = ctx["units"]

    df = read_sql(
        "SELECT extract(doy from valid) as doy, sknt, drct from alldata "
        "where station = %s and sknt >= 0 and drct >= 0 and report_type = 2",
        asos,
        params=(station,),
        index_col=None,
    )
    if df.empty:
        raise NoDataFound("No data Found.")

    # Compute components in MPS
    u, v = wind_components(
        (df["sknt"].values * units("knot")).to(units("meter / second")),
        df["drct"].values * units("degree"),
    )
    df["u"] = u.m
    df["v"] = v.m
    gdf = df.groupby(by="doy").mean()
    u = (
        (gdf["u"].values * units("meter / second"))
        .to(XREF_UNITS[plot_units])
        .m
    )
    v = (
        (gdf["v"].values * units("meter / second"))
        .to(XREF_UNITS[plot_units])
        .m
    )
    mag = (gdf["sknt"].values * units("knot")).to(XREF_UNITS[plot_units]).m

    df2 = pd.DataFrame(
        dict(
            u=pd.Series(u),
            v=pd.Series(v),
            mag=pd.Series(mag),
            day_of_year=pd.Series(np.arange(1, 367)),
        )
    )

    (fig, axes) = plt.subplots(2, 1, figsize=(8, 9))
    ax = axes[0]
    ax.plot(
        np.arange(1, 366),
        smooth(u[:-1]),
        color="r",
        label="u, West(+) : East(-) component",
        lw=2,
    )
    ax.plot(
        np.arange(1, 366),
        smooth(v[:-1]),
        color="b",
        label="v, South(+) : North(-) component",
        lw=2,
    )
    ax.set_xticks([1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
    ax.set_xticklabels(calendar.month_abbr[1:])
    ax.legend(ncol=2, fontsize=11, loc=(0.0, -0.21))
    ax.grid(True)
    ax.set_xlim(0, 366)
    ab = ctx["_nt"].sts[station]["archive_begin"]
    if ab is None:
        raise NoDataFound("Unknown station metadata.")
    ax.set_title(
        (
            "[%s] %s Daily Average Component Wind Speed\n"
            "[%s-%s] 7 day smooth filter applied, %.0f obs found"
        )
        % (
            station,
            ctx["_nt"].sts[station]["name"],
            ab.year,
            datetime.datetime.now().year,
            len(df.index),
        )
    )
    ax.set_ylabel("Average Wind Speed %s" % (PDICT.get(plot_units),))

    box = ax.get_position()
    ax.set_position(
        [box.x0, box.y0 + box.height * 0.1, box.width, box.height * 0.9]
    )

    ax = axes[1]
    ax.plot(
        np.arange(1, 366),
        smooth(mag[:-1]),
        color="g",
        lw=2,
        label="Speed Magnitude",
    )
    ax.legend(loc="best")
    ax.set_xticks([1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
    ax.set_xticklabels(calendar.month_abbr[1:])
    ax.set_ylabel("Average Speed %s" % (PDICT[plot_units],))
    ax.grid(True)
    ax.set_xlim(0, 366)

    return fig, df2


if __name__ == "__main__":
    plotter(dict(station="AMW", network="IA_ASOS"))
