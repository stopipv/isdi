from MobileDevice import list_devices, InstallationProxy
a = list(list_devices().items())
k, d = a[0]
print(k, d)
d.connect()

ip = InstallationProxy(d)
print(ip.lookup_applications())
