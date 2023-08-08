from abc import ABC
from typing import List

from superagi.tools.base_tool import BaseToolkit, BaseTool

# Local shopify specific imports
from shopify_llm import LLMInput, ShopifyLLM
from shopify_config import ShopifyConfig
from get_product_data import ProductDataTool
from create_product import CreateProductTool
from get_all_products import GetAllProductsTool
from get_basic_product_data import GetProductTool
from search_products import SearchProductsTool
from update_product import UpdateProductTool
from delete_product import DeleteProductTool



class ShopifyToolkit(BaseToolkit, ABC):
    name: str = "Shopify Toolkit"
    description: str = "Shopify Tool kit contains all tools related to shopify tasks"

    def get_tools(self) -> List[BaseTool]:
        return [ProductDataTool(), CreateProductTool(), GetAllProductsTool(), GetProductTool(), SearchProductsTool(), UpdateProductTool(), DeleteProductTool()]

    def get_env_keys(self) -> List[str]:
        return ["SHOPIFY_API_KEY", "SHOPIFY_API_SECRET", "SHOPIFY_PASSWORD", "STORE_URL", "API_VERSION", "STORE_PROTOCOL"]
