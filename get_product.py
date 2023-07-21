import shopify
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

class GetProductInput(BaseModel):
    product_identifier: Union[str, int] = Field(
        ..., 
        description= "The ID or the title of the product to fetch."
    )


class GetProductTool(BaseTool):
    """
    Get Product Tool
    Attributes:
        name : The name of the tool.
        description : The description of the tool.
        args_schema : The args schema.
    """
    name: str = "Get Product"
    description: str = "Fetch basic product information from Shopify"
    args_schema: Type[BaseModel] = GetProductInput

    class Config:
        arbitrary_types_allowed = True

    def _execute(self, product_identifier: Union[str, int]) -> Optional[Dict[str, Union[str, List[Dict[str, str]]]]]:
        """
        Execute the get product tool.
        Args:
            product_identifier : The ID or the title of the product to fetch.
        Returns:
            A dictionary containing the product attributes if found, or None otherwise.
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
        # Compute the new lines outside of f-string
        metafields_values = ',\n'.join(
            [metafield.value for metafield in product.metafields()])
        # Get all collections that contain the product
        collections = shopify.CustomCollection.find(product_id=product.id)
        collections.extend(shopify.SmartCollection.find(product_id=product.id))
        collections_names = ', '.join(
            [collection.title for collection in collections])

        product_details = f"""
            Title: {product.title}

            Description: 
            {self.html_to_plain_text(product.body_html)}

            Product Type: {product.product_type}

            Vendor: {product.vendor}

            Collections:
            {collections_names}

            Tags:
            {product.tags}

            Price: {product.variants[0].price if product.variants else None}

            Product ID: {product.id}

            Product Metafields:
            {', '.join([str(metafield) for metafield in product.metafields()])}

            Metafields Values: 
            {metafields_values}
        """
        return product_details

    def _log_product_details(self, product_details):
        logger.info(product_details)

    def html_to_plain_text(self, html):
        """
        Convert HTML to plain text.

        Args:
            html (str): The HTML string.

        Returns:
            str: The converted plain text string.
        """
        if not isinstance(html, str):
            logger.error("html must be a string")
            raise ValueError("html must be a string")
    
        soup = BeautifulSoup(html, "html.parser")
        text = '\n'.join(p.get_text() for p in soup.find_all('p'))
        return text