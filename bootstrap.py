from vmanage.api.http_methods import HttpMethods
from vmanage.api.device import Device

"""

The python viptela SDK does not have built-in function to download the bootstrap file.

To leverage the SDK we can extend an existing class to help us build the requests and create a new method without
having to rewrite lots of code.

"""

class Bootstrap(Device):

    def __init__(self, session, host, port=443):
        """Initialize Extended Device Inventory object with session parameters.

        Args:
            session (obj): Requests Session object
            host (str): hostname or IP address of vManage
            port (int): default HTTPS 443
        """
        super().__init__(session, host, port)

    def get_bootstrap_config(self, uuid):

        # example URL - https://x.x.x.x/dataservice/system/device/bootstrap/device/C1113-8P-FCZ2634R0T6?configtype=cloudinit&inclDefRootCert=false&version=v1

        url = f"{self.base_url}system/device/bootstrap/device/{uuid}?configtype=cloudinit&inclDefRootCert=false&version=v1"
        response = HttpMethods(self.session, url).request('GET')
        return response
