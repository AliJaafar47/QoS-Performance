## -*- mode: python; coding: utf-8 -*-

# Mixin include file to add extra hosts to ping


PING_HOSTS=get_test_parameter('ping_hosts', default=[], split=True)
PING_LOCAL_BINDS=get_test_parameter('ping_local_binds', default=[], split=True)

for host, local_bind in zip_longest(PING_HOSTS, PING_LOCAL_BINDS):
    if not host:
        break
    DATA_SETS['Page Loading time %s (extra)' % host] = {'ip_version': IP_VERSION,
    												 'interval': STEP_SIZE,
                                                     'length': TOTAL_LENGTH,
                                                     'host': host,
                                                     'local_bind': local_bind,
                                                     'units': 'ms',
                                                     'id': host,
                                                     'runner': 'WMM'}

