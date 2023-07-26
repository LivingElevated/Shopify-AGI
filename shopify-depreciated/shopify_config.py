import shopify
from superagi.config.config import get_config


class ShopifyConfig:
    """
    Shopify Configurations for AutoGPT integrations
    """

    def __init__(self):
        self.shopify_api_key = get_config("SHOPIFY_API_KEY")
        self.shopify_api_secret = get_config("SHOPIFY_API_SECRET")
        self.shopify_password = get_config("SHOPIFY_PASSWORD")
        self.store_url = get_config("STORE_URL")
        self.api_version = get_config("API_VERSION")
        self.protocol = get_config("STORE_PROTOCOL")
        print('Starting Shopify Connection...')
        print('api_key:', self.shopify_api_key)
        print('api_version:', self.api_version)
        print('domain:', self.store_url)
        print('password:', self.shopify_password)
        print('protocol:', self.protocol)

        self.shop = None

        # Initialize Shopify API
        if all([
            self.shopify_api_key,
            self.shopify_api_secret,
            self.shopify_password,
            self.store_url,
            self.api_version
        ]):
            print('Authenticating to Shopify...')
            # Authenticating to Shopify
            self.session = shopify.Session(
                self.store_url, self.api_version, self.shopify_password)
            self.client = shopify.ShopifyResource.activate_session(
                self.session)
            self.shop = shopify.Shop.current()
            print('Shopify Authentication Complete')
        else:
            print("Shopify credentials not found in the config.")

    def get_shop(self):
        return self.shop