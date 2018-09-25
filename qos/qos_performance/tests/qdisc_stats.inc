## -*- mode: python; coding: utf-8 -*-

# Mixin include file to add qdisc stats to a test


QDISC_STATS_HOSTS=get_test_parameter('qdisc_stats_hosts', default=[], split=True)
QDISC_STATS_IFACES=get_test_parameter('qdisc_stats_interfaces', default=[], split=True)
for host,iface in zip(QDISC_STATS_HOSTS, QDISC_STATS_IFACES):
    id = "%s (%s)" % (host, iface)
    DATA_SETS['qdisc_stats_%s' % host] = {'interface': iface,
                                          'interval': STEP_SIZE,
                                          'length': TOTAL_LENGTH,
                                          'host': host,
                                          'id': id,
                                          'units': 'misc',
                                          'runner': 'tc'}
    DATA_SETS['qdisc_stats_%s::dropped' % host] = {'units': 'packets', 'runner': 'null', 'id': id}
    DATA_SETS['qdisc_stats_%s::ecn_mark' % host] = {'units': 'packets', 'runner': 'null', 'id': id}
