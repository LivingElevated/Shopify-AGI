import shopify
import json
from typing import Type, Union, Dict, Any, List, Optional, Tuple

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Local application/library specific imports
from superagi.tools.base_tool import BaseTool
from superagi.tools.shopify.shopify_llm import LLMInput, ShopifyLLM
from superagi.tools.shopify.shopify_config import ShopifyConfig
from superagi.llms.base_llm import BaseLlm
from superagi.resource_manager.file_manager import FileManager
from superagi.lib.logger import logger
from superagi.tools.tool_response_query_manager import ToolResponseQueryManager


class AllProductDataInput(BaseModel):
    product_identifier: Union[str, int] = Field(
        ...,
        description="The ID or the title of the product to fetch."
    )


class AllProductDataTool(BaseTool):
    """
    All Product Data Tool
    Attributes:
        name : The name of the tool.
        description : The description of the tool.
        args_schema : The args schema.
    """
    name: str = "All Product Data"
    description: str = "Fetch all product information from Shopify"
    args_schema: Type[BaseModel] = AllProductDataInput

    class Config:
        arbitrary_types_allowed = True
        
    def _execute(self, product_identifier: Union[str, int]) -> Optional[Dict[str, Union[str, List[Dict[str, str]]]]]:
        """
        Execute the get product tool.
        Args:
            product_identifier : The ID or the title of the product to fetch.
        Returns:
            A dictionary containing all the product attributes if found, or None otherwise.
        """
        shop = self._init_shopify()
        product = self._get_product_by_identifier(shop, product_identifier)

        if product:
            product_details_str = self._generate_product_details(product)
            self._log_product_details(product_details_str)

            return product_details_str

        return None

    def _init_shopify(self):
        shop_config = ShopifyConfig()
        return shop_config.get_shop()

    def _get_product_by_identifier(self, shop, product_identifier):
        # If the identifier is numeric, it's treated as an ID.
        if str(product_identifier).isdigit():
            product_id = int(product_identifier)
            return shopify.Product.find(product_id)
        else:
            all_products = shopify.Product.find()
            return next((p for p in all_products if p.title.lower() == product_identifier.lower()), None)

    def _generate_product_details(self, product):
        # Convert the product object to a dictionary
        product_data = product.to_dict()

        # Pretty print all product details
        product_details = json.dumps(product_data, indent=2)

        return product_details

    def _log_product_details(self, product_details):
        logger.info(product_details)
