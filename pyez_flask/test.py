import config 

def get_ip_addr(hostname):
  f = open('/home/thanzawa/pyez_app/pyez_flask/host_addr.txt', 'r')
  hosts = f.read().split('\n')
  for host in hosts:
    if hostname == host.split(',')[0]:
      print host.split(',')[1].rstrip()
      return host.split(',')[1].rstrip()


get_ip_addr('gundam-re0')
