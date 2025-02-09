"""JSON service emitting observation history for a given date"""
import json
import os
import datetime

from pandas.io.sql import read_sql
from dateutil.parser import parse
from pymemcache.client import Client
from paste.request import parse_formvars
from pyiem.reference import IEMVARS
from pyiem.util import get_sqlalchemy_conn, html_escape


def do_today(table, station, network, date):
    """Our backend is current_log"""
    cols = ["local_valid", "utc_valid", "tmpf", "sknt", "gust", "drct"]
    table["fields"] = [IEMVARS[col] for col in cols]
    with get_sqlalchemy_conn("iem") as conn:
        df = read_sql(
            """
            select
            to_char(valid at time zone tzname,
                    'YYYY-MM-DDThh24:MI:SS') as local_valid,
            to_char(valid at time zone 'UTC',
                    'YYYY-MM-DDThh24:MI:SSZ') as utc_valid,
            tmpf, sknt, gust, drct from current_log c JOIN stations t
            on (c.iemid = t.iemid) WHERE date(valid at time zone tzname) = %s
            and t.id = %s and t.network = %s ORDER by local_valid
        """,
            conn,
            params=(date, station, network),
            index_col=None,
        )
    table["rows"] = [row for row in df.itertuples(index=False)]


def do_asos(table, station, _network, date):
    """Our backend is ASOS"""
    cols = ["local_valid", "utc_valid", "tmpf", "sknt", "gust", "drct"]
    table["fields"] = [IEMVARS[col] for col in cols]
    with get_sqlalchemy_conn("asos") as conn:
        df = read_sql(
            """
            select
            to_char(valid at time zone tzname,
                    'YYYY-MM-DDThh24:MI:SS') as local_valid,
            to_char(valid at time zone 'UTC',
                    'YYYY-MM-DDThh24:MI:SSZ') as utc_valid,
            tmpf, sknt, gust, drct from alldata a JOIN stations t
            on (a.station = t.id) WHERE date(valid at time zone tzname) = %s
            and station = %s ORDER by local_valid
        """,
            conn,
            params=(date, station),
            index_col=None,
        )
    table["rows"] = [row for row in df.itertuples(index=False)]


def workflow(station, network, date):
    """Go get the dictionary of data we need and deserve"""
    date = parse(date).date()
    table = {"fields": [], "rows": []}
    if date == datetime.date.today():
        do_today(table, station, network, date)
    elif network.find("ASOS") > -1:
        do_asos(table, station, network, date)

    return json.dumps(table)


def application(environ, start_response):
    """Answer request."""
    fields = parse_formvars(environ)

    station = fields.get("station", "AMW")
    network = fields.get("network", "IA_ASOS")
    date = fields.get("date", "2016-01-01")
    cb = fields.get("callback", None)

    hostname = os.environ.get("SERVER_NAME", "")
    mckey = f"/json/obhistory/{station}/{network}/{date}"
    mc = Client("iem-memcached:11211")
    res = mc.get(mckey) if hostname != "iem.local" else None
    if not res:
        res = workflow(station, network, date).replace("NaN", "null")
        mc.set(mckey, res, 3600)
    else:
        res = res.decode("utf-8")
    mc.close()
    if cb is not None:
        res = f"{html_escape(cb)}({res})"

    headers = [("Content-type", "application/json")]
    start_response("200 OK", headers)
    return [res.encode("ascii")]
