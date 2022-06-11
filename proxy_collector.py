import concurrent.futures
from pathlib import Path
from tqdm import tqdm
import requests
import logging
import yaml
import re
import os

# disable https warnings
import urllib3
urllib3.disable_warnings()

class proxy_collector():
    def __init__(self, cfg_path="cfg/options.yaml") -> None:
        logging.basicConfig(level=logging.INFO, format="[Proxy Collector] (%(levelname)s) %(message)s", handlers=[logging.StreamHandler()])
        self.__set_options(cfg_path)
        self.proxies=[]
        self.proxies_temp=[]

    def __set_options(self, cfg_path):
        options = self.__read_yaml_file(cfg_path)

        # proxy_options
        self.proxy_URLs = options["proxy_URLs"]
        self.proxy_testing_ip = options["proxy_testing_ip"]
        self.proxy_filter_pattern = options["proxy_filter_pattern"]
        self.proxy_save_file = options["proxy_save_file"]
        self.proxy_testing_threads = options["proxy_testing_threads"]
        self.proxy_testing_timeout = options["proxy_testing_timeout"]
        self.proxy_schemas = options["proxy_schemas"]
        self.verbose = options["verbose"]

    @staticmethod
    def __read_yaml_file(cfg_path):
        with open(cfg_path, 'r', encoding='utf8') as stream:
            data_loaded = yaml.safe_load(stream)
        return data_loaded

    @staticmethod
    def __write_to_file(to_write, file_name, write_mode="w"):
        file_path, _ = os.path.split(file_name)
        Path(file_path).mkdir(parents=True, exist_ok=True)
        
        with open(file_name, write_mode, encoding='utf-8') as file:
            for item in to_write:
                file.write(str(item))
                file.write("\n")

    def __get_proxies(self):
        logging.info("Getting proxies")
        with tqdm(total=len(self.proxy_URLs)) as pbar:
            for proxy_URL in self.proxy_URLs:
                try:
                    res = requests.get(proxy_URL, verify=False).text
                    matched_IPs = re.findall(self.proxy_filter_pattern, res)
                    self.proxies_temp += matched_IPs
                except Exception as e:
                    logging.exception("{} is unreachable".format(proxy_URL))
                finally:
                    pbar.update(1)

    def __test_proxies(self):
        def try_proxy(proxy, index):
            try:
                proxy_with_schema = self.__build_proxy_schema(proxy) # {"http":f"socks5h://{proxy}", "https":f"socks5h://{proxy}"}
                res = requests.get(self.proxy_testing_ip, proxies=proxy_with_schema, timeout=self.proxy_testing_timeout, verify=False)
                # logging.info("{0}- Pass {1} Response {2}\n".format(index, proxy, res.json()['origin']))
                self.proxies.append(proxy)
            except requests.exceptions.ConnectTimeout as e:
                if(self.verbose):
                    logging.warning("{0}- Timeout {1}\n".format(index, proxy))
            except requests.exceptions.ProxyError as e:
                if(self.verbose):
                    logging.warning("{0}- Proxy error {1}\n".format(index, proxy))
            except Exception as e:
                if(self.verbose):
                    logging.warning("{0}- Error {1}\n".format(index, proxy, e))


        logging.info("Testing proxies")
        with tqdm(total=len(self.proxies_temp)) as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.proxy_testing_threads) as executor:
                futures = [executor.submit(try_proxy, proxy, index) for index, proxy in enumerate(self.proxies_temp)]

                for future in concurrent.futures.as_completed(futures):
                    _ = future.result()
                    pbar.update(1)


        logging.info("Test compleated, working proxy count: {} out of {}".format(len(self.proxies), len(self.proxies_temp)))
        self.__write_to_file(self.proxies, self.proxy_save_file)
        logging.info("Proxies saved")


    def __build_proxy_schema(self, proxy):
        proxy_with_schema = {}
        for proxy_schema in self.proxy_schemas:
            proxy_with_schema.update({proxy_schema:self.proxy_schemas[proxy_schema].format(proxy)})
        return proxy_with_schema


    def fetch_proxies(self):
        self.__get_proxies()
        self.__test_proxies()



if __name__ == "main":
    pc = proxy_collector()
    pc.fetch_proxies()
