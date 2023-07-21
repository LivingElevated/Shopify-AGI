from abc import ABC
from typing import List

from superagi.tools.base_tool import BaseToolkit, BaseTool
from superagi.tools.shopify.all_product_data import AllProductDataTool
from superagi.tools.shopify.create_product import CreateProductTool
from superagi.tools.shopify.get_all_products import GetAllProductsTool
from superagi.tools.shopify.get_product import GetProductTool
# from superagi.tools.shopify.update_product import UpdateProductTool


class ShopifyToolkit(BaseToolkit, ABC):
    name: str = "Shopify Toolkit"
    description: str = "Shopify Tool kit contains all tools related to shopify tasks"

    def get_tools(self) -> List[BaseTool]:
        return [AllProductDataTool(), CreateProductTool(), GetAllProductsTool(), GetProductTool()]

    def get_env_keys(self) -> List[str]:
        return ["SHOPIFY_API_KEY", "SHOPIFY_API_SECRET", "SHOPIFY_PASSWORD", "STORE_URL", "API_VERSION", "STORE_PROTOCOL"]
