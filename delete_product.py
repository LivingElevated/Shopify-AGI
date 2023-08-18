import shopify
import json
from textwrap import dedent
from typing import Type, Union, Dict, Any, List, Optional, Tuple

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Local application/library specific imports
from superagi.tools.base_tool import BaseTool
from superagi.resource_manager.file_manager import FileManager
from superagi.llms.base_llm import BaseLlm
from superagi.resource_manager.file_manager import FileManager
from superagi.lib.logger import logger
from superagi.tools.tool_response_query_manager import ToolResponseQueryManager

# Local shopify specific imports
from shopify_llm import LLMInput, ShopifyLLM
from shopify_config import ShopifyConfig


class DeleteProductInput(BaseModel):
    product_id: str = Field(
        ..., 
        description= "The ID of the product to delete. Must be a number. (Must be called by the product ID to avoid accidental deletion)"
    )


class DeleteProductTool(BaseTool):
    """
    Delete Product Tool
    Attributes:
        name : The name of the tool.
        description : The description of the tool.
        args_schema : The args schema.
    """
    name: str = "Delete Product"
    description: str = "Delete a single product from your Shopify store. (Must be called by the product ID)"
    args_schema: Type[BaseModel] = DeleteProductInput
    resource_manager: Optional[FileManager] = None

    class Config:
        arbitrary_types_allowed = True

    def _execute(self, product_id: str) -> Optional[Dict[str, Union[str, List[Dict[str, str]]]]]:
        """
        Delete a product from Shopify.
        Args:

        product_id(str): The ID of the product to delete.

        Returns:
            A dictionary containing the product attributes if found, or None otherwise.
        """
        shop = self._init_shopify()

        product = self._get_product_by_identifier(shop, product_id)

        if product:
            product_details_str = self._generate_product_details(product)
            self._log_product_details(product_details_str)
            product.destroy()
            file_name = f"Product ID {product_id}.csv"
            # Write product details to a file
            self.resource_manager.write_file(file_name, product_details_str)

            delete_message = dedent(f"""
                                    Successfully deleted Product ID: {product.id}
                                    Backup written to file: "{file_name}" in the current resource manager output directory.

                                    Product Details:
                                    {product_details_str}
                                    
                                    """)

            return delete_message
        
        else:
            logger.info(f"Product {product_id} not found.")
            print(f"Product {product_id} not found.")
            return ValueError(f"Product {product_id} not found.")
        
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

        # Compute the new lines outside of f-string
        metafields_values = ',\n'.join(
            [metafield.value for metafield in product.metafields()])
        # Get all collections that contain the product
        collections = shopify.CustomCollection.find(product_id=product.id)
        collections.extend(shopify.SmartCollection.find(product_id=product.id))
        collections_names = ', '.join(
            [collection.title for collection in collections])

        # Generate a pretty formatted output
        product_details = dedent(f"""
            Title: {product.title}

            Description:
            {self.html_to_plain_text(product.body_html)}

            Product Type: {product.product_type}

            Vendor: {product.vendor}

            Collections: {collections_names}

            Tags: {product.tags}

            Price: {product.variants[0].price if product.variants else None}

            Product ID: {product.id}

            Product Metafields: {', '.join([str(metafield) for metafield in product.metafields()])}

            Metafields Values: {metafields_values}

            Images: {json.dumps(product_data["images"], indent=2)}

            Variants: {json.dumps(product_data["variants"], indent=2)}

            Options: {json.dumps(product_data["options"], indent=2)}

            Published At: {product.published_at}

            Created At: {product.created_at}

            Updated At: {product.updated_at}

        """)

        return product_details

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

    def _log_product_details(self, product_details):
        logger.info(product_details)