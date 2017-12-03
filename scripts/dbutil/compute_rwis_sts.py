"""Figure out when the RWIS data started..."""
from __future__ import print_function
import sys
import datetime

import pytz
from pyiem.network import Table as NetworkTable
from pyiem.util import get_dbconn


def main():
    """Go Main"""
    basets = datetime.datetime.now()
    basets = basets.replace(tzinfo=pytz.timezone("America/Chicago"))

    rwis = get_dbconn('rwis')
    rcursor = rwis.cursor()
    mesosite = get_dbconn('mesosite')
    mcursor = mesosite.cursor()

    net = sys.argv[1]
    table = NetworkTable(net)

    rcursor.execute("""SELECT station, min(valid), max(valid) from alldata
                    GROUP by station ORDER by min ASC""")
    for row in rcursor:
        station = row[0]
        if station not in table.sts:
            continue
        if table.sts[station]['archive_begin'] != row[1]:
            print(('Updated %s STS WAS: %s NOW: %s'
                   '') % (station, table.sts[station]['archive_begin'],
                          row[1]))

        mcursor.execute("""UPDATE stations SET archive_begin = %s
             WHERE id = %s and network = %s""", (row[1], station, net))
        if mcursor.rowcount == 0:
            print('ERROR: No rows updated')

    mcursor.close()
    mesosite.commit()
    mesosite.close()


if __name__ == '__main__':
    main()
