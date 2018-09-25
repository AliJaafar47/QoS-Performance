## -*- mode: python; coding: utf-8 -*-

# Mixin include file to add cpu stats to a test


CPU_STATS_HOSTS=get_test_parameter('cpu_stats_hosts', default=[], split=True)
for host in CPU_STATS_HOSTS:
    DATA_SETS['cpu_stats_%s' % host] = {'interval': STEP_SIZE,
                                        'length': TOTAL_LENGTH,
                                        'host': host,
                                        'units': 'misc',
                                        'id': host,
                                        'runner': 'cpu_stats'}
