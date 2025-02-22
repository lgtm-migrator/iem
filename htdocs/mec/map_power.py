"""
  Generate a simple scatter plot of power...
"""
from io import BytesIO
import datetime

import numpy as np
import matplotlib.colors as mpcolors
import matplotlib.colorbar as mpcolorbar
import matplotlib.patheffects as PathEffects
from paste.request import parse_formvars
from metpy.calc import wind_components
from metpy.units import units
from pyiem.plot.use_agg import plt
from pyiem.plot import get_cmap
from pyiem.util import get_dbconn


def make_colorbar(clevs, norm, cmap):
    """Manual Color Bar"""

    ax = plt.axes([0.02, 0.1, 0.05, 0.8], frameon=False, yticks=[], xticks=[])

    under = clevs[0] - (clevs[1] - clevs[0])
    over = clevs[-1] + (clevs[-1] - clevs[-2])
    blevels = np.concatenate([[under], clevs, [over]])
    cb2 = mpcolorbar.ColorbarBase(
        ax,
        cmap=cmap,
        norm=norm,
        boundaries=blevels,
        extend="both",
        ticks=None,
        spacing="uniform",
        orientation="vertical",
    )
    for i, lev in enumerate(clevs):
        y = float(i) / (len(clevs) - 1)
        fmt = "%g"
        txt = cb2.ax.text(0.5, y, fmt % (lev,), va="center", ha="center")
        txt.set_path_effects(
            [PathEffects.withStroke(linewidth=2, foreground="w")]
        )

    ax.yaxis.set_ticklabels([])


def do(valid, yawsource):
    """Generate plot for a given timestamp"""
    if yawsource not in ["yaw", "yaw2", "yaw3"]:
        return
    yawdict = {"yaw": "Orginal", "yaw2": "daryl corrected", "yaw3": "daryl v2"}
    pgconn = get_dbconn("mec")
    cursor = pgconn.cursor()

    cursor.execute(
        """select turbineid, power, ST_x(geom), ST_y(geom),
    """
        + yawsource
        + """, windspeed, pitch
     from sampled_data s JOIN turbines t on (t.id = s.turbineid)
     WHERE valid = %s and power is not null and """
        + yawsource
        + """ is not null
     and windspeed is not null and pitch is not null""",
        (valid,),
    )
    lons = []
    lats = []
    vals = []
    u = []
    v = []
    ws = []
    yaw = []
    pitch = []
    for row in cursor:
        lons.append(row[2])
        lats.append(row[3])
        vals.append(row[1])
        ws.append(row[5])
        yaw.append(row[4])
        a, b = wind_components(
            units("meter / second") * row[5], units("degree") * row[4]
        )
        u.append(a.m)
        v.append(b.m)
        pitch.append(row[6])
    pitch = np.array(pitch)
    vals = np.array(vals)
    avgv = np.average(vals)
    # vals2 = vals - avgv
    fig = plt.figure(figsize=(12.8, 7.2))
    ax = fig.add_axes([0.14, 0.1, 0.52, 0.8])

    cmap = get_cmap("jet")
    cmap.set_under("tan")
    cmap.set_over("black")
    clevs = np.arange(0, 1651, 150)
    norm = mpcolors.BoundaryNorm(clevs, cmap.N)
    ax.quiver(lons, lats, u, v, zorder=1)
    ax.scatter(
        lons,
        lats,
        c=vals,
        norm=norm,
        edgecolor="none",
        cmap=cmap,
        s=100,
        zorder=2,
    )
    ax.get_yaxis().get_major_formatter().set_useOffset(False)
    ax.get_xaxis().get_major_formatter().set_useOffset(False)
    ax.set_title(
        (
            "Farm Turbine Power [kW] (1min sampled dataset)\n"
            "Valid: %s, yaw source: %s"
        )
        % (
            valid.strftime("%d %b %Y %I:%M %p"),
            yawdict.get(yawsource, yawsource),
        )
    )
    make_colorbar(clevs, norm, cmap)

    ax.text(
        0.05,
        0.05,
        "Turbine Power: $\mu$= %.1f $\sigma$= %.1f kW" % (avgv, np.std(vals)),
        transform=ax.transAxes,
    )
    ax.text(
        0.05,
        0.01,
        "Wind $\mu$= %.1f $\sigma$= %.1f $ms^{-1}$"
        % (np.average(ws), np.std(ws)),
        transform=ax.transAxes,
    )
    ax.set_xlabel(r"Longitude $^\circ$E")
    ax.set_ylabel(r"Latitude $^\circ$N")
    ax.set_xlim(-94.832, -94.673)
    ax.set_ylim(42.545, 42.671)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])

    # Next plot
    ax2 = fig.add_axes([0.7, 0.80, 0.28, 0.18])
    ax2.scatter(ws, vals, edgecolor="k", c="k")
    ax2.text(
        0.5,
        -0.25,
        "Wind Speed $ms^{-1}$",
        transform=ax2.transAxes,
        ha="center",
    )
    ax2.set_xlim(0, 20)
    # ax2.set_ylabel("Power kW")
    ax2.grid(True)

    # Next plot
    ax3 = fig.add_axes([0.7, 0.57, 0.28, 0.18], sharey=ax2)
    ax3.scatter(yaw, vals, edgecolor="k", c="k")
    ax3.text(0.5, -0.25, "Yaw", transform=ax3.transAxes, ha="center")
    # ax3.set_ylabel("Power kW")
    ax3.set_xlim(0, 360)
    ax3.set_xticks(np.arange(0, 361, 45))
    ax3.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"])
    ax3.grid(True)

    # Next plot
    ax4 = fig.add_axes([0.7, 0.32, 0.28, 0.18], sharey=ax2)
    ax4.scatter(pitch, vals, edgecolor="k", c="k")
    ax4.text(
        0.5, -0.25, "Pitch $^\circ$", transform=ax4.transAxes, ha="center"
    )
    ax4.set_ylim(-10, 1600)
    ax4.grid(True)

    # Next plot
    ax5 = fig.add_axes([0.7, 0.07, 0.28, 0.18], sharex=ax4)
    ax5.scatter(pitch, ws, edgecolor="k", c="k")
    ax5.text(
        0.5, -0.25, "Pitch $^\circ$", transform=ax5.transAxes, ha="center"
    )
    ax5.grid(True)
    ax5.set_ylim(bottom=-10)
    # maxpitch = max(np.where(pitch > 20, 0, pitch))
    # ax5.set_xlim(np.ma.minimum(pitch)-0.5, maxpitch+0.5)
    ax5.set_xlim(-3, 20.1)
    ax5.set_ylim(0, 20)
    ax5.text(
        -0.1,
        0.5,
        "Wind Speed $ms^{-1}$",
        transform=ax5.transAxes,
        ha="center",
        va="center",
        rotation=90,
    )


def application(environ, start_response):
    """Go Main Go"""
    form = parse_formvars(environ)
    ts = form.get("ts", "200006302000")
    ts = datetime.datetime.strptime(ts, "%Y%m%d%H%M")
    yawsource = form.get("yawsource", "yaw")
    headers = [("Content-type", "image/png")]
    start_response("200 OK", headers)
    bio = BytesIO()
    do(ts, yawsource)
    plt.savefig(bio)
    return [bio.getvalue()]
