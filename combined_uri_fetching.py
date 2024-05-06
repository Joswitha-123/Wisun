import re
import asyncio
from aiocoap import Context, Message
from aiocoap.numbers.codes import GET
from pydbus import SystemBus
from datetime import datetime

# Define function to get IPv6 addresses of connected nodes
def get_nodes_ipv6_addresses():
    """
    Retrieves and returns a list of IPv6 addresses for all connected nodes.

    Returns:
        list: A list of formatted IPv6 addresses or an empty list if no nodes are found.
    """
    bus = SystemBus()
    proxy = bus.get("com.silabs.Wisun.BorderRouter", "/com/silabs/Wisun/BorderRouter")

    nodes = proxy.Nodes
    ipv6_list = []

    def sliceIPv6(source):
        return [source[i:i + 4] for i in range(0, len(source), 4)]

    def prettyIPv6(ipv6):
        ipv6 = ":".join(sliceIPv6(ipv6))
        ipv6 = re.sub("0000:", ":", ipv6)
        ipv6 = re.sub(":{2,}", "::", ipv6)
        return ipv6

    if "ipv6" in nodes[0][1]:
        # D-BUS API < 2.0
        for node in nodes:
            # D-Bus API < 2.0
            if len(node[1]["ipv6"]) != 2:
                continue
            if "parent" not in node[1] and (
                "node_role" not in node[1] or node[1]["node_role"] != 2
            ):
                continue

            ipv6 = bytes(node[1]["ipv6"][1]).hex()
            ipv6_list.append(prettyIPv6(ipv6))
    else:
        # D-BUS API >= 2.0
        topology = proxy.RoutingGraph
        for node in topology:
            ipv6 = bytes(node[0]).hex()
            ipv6_list.append(prettyIPv6(ipv6))

    return ipv6_list

# Define function to fetch data from CoAP URI and print variable and value lists
async def fetch_and_print_node_data(ip_address):
    """
    Fetches data from the provided CoAP URI and prints variable and value lists.

    Args:
        ip_address (str): The IPv6 address of the node in the format "coap://[...]:5683/om2m".
    """
    async def coap_get(uri):
        print(f"Fetching resource from {uri}")
        protocol = await Context.create_client_context()
        request = Message(code=GET, uri=uri)

        try:
            response = await protocol.request(request).response
            return response.payload.decode('utf-8')
        except Exception as e:
            print(f'Failed to fetch resource from {uri}:')
            print(e)
            return None

    async def get_and_parse_data(uri):
        try:
            response = await coap_get(uri)

            if response is None:
                print(f"No response received from {uri}")
                return None, None, None

            # Regular expression to match key-value pairs
            pattern = r'"([^"]+?)":(.+?)(?:,|\})'

            # Initialize empty lists
            data_list = []
            variable_list = []
            value_list = []
            
            # Adding timestamp variable and its value
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            variable_list.append('timestamp')
            value_list.append(timestamp)

            # Extract key-value pairs and separate variables/values
            matches = re.findall(pattern, response.strip())
            for key, value in matches:
                data_list.append({key: value})
                variable_list.append(key)
                value_list.append(value)
            
        
            return data_list, variable_list, value_list
        except Exception as e:
            print(f"An error occurred while fetching and parsing data from {uri}: {e}")
            return None, None, None

    print(f"Fetching and printing data for {ip_address}")
    data, variable_list, value_list = await get_and_parse_data(ip_address)

    if data is None:
        print("Failed to fetch data from the URI.")
    else:
        # You can process or print the data list here (optional)
        # ...

        # Print variable and value lists
        output_var = '[' + ', '.join(variable_list) + ']'
        output_val = '[' + ', '.join(map(str, value_list)) + ']'

        print(f"Node Information for {ip_address}:")
        print("Variable List:", output_var)
        print("Value List:", output_val)


if __name__== '__main__':
    # Get IPv6 addresses of connected nodes
    ipv6_addresses = get_nodes_ipv6_addresses()

    # Traverse through list from the second element
    for ipv6_address in ipv6_addresses[1:]:
        # Format IPv6 address with "coap://" prefix
        uri = f"coap://[{ipv6_address}]:5683/om2m"
        
        # Call fetch_and_print_node_data function for each IPv6 address
        asyncio.run(fetch_and_print_node_data(uri))
