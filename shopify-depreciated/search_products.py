import shopify
from tabulate import tabulate
from typing import Type, Union, Dict, Any, List, Optional, Tuple

from pydantic import BaseModel, Field, root_validator


# Local application/library specific imports
from superagi.tools.base_tool import BaseTool
from superagi.tools.shopify.shopify_llm import LLMInput, ShopifyLLM
from superagi.tools.shopify.shopify_config import ShopifyConfig
from superagi.llms.base_llm import BaseLlm
from superagi.resource_manager.file_manager import FileManager
from superagi.lib.logger import logger
from superagi.tools.tool_response_query_manager import ToolResponseQueryManager


class SearchProductsInput(BaseModel):
    title: Optional[str] = Field(
        None,
        description="Title of the products to search for."
    )
    product_type: Optional[str] = Field(
        None,
        description="Product type to filter the search."
    )
    vendor: Optional[str] = Field(
        None,
        description="Vendor to filter the search."
    )
    sortby: Optional[str] = Field(
        None, 
        description="Sort method to use (use default if nothing is specified): default, alpha-asc, alpha-desc, price-asc, price-desc"
        )
    output: Optional[List[str]] = Field(
        None, 
        description="Output to be returned by tool. Default is Product ID, Title, Price."
        )



class SearchProductsTool(BaseTool):
    """
    Search Products Tool
    Attributes:
        name : The name of the tool.
        description : The description of the tool.
        args_schema : The args schema.
    """
    name: str = "Search Products"
    description: str = "Search products in Shopify based on various criteria"
    args_schema: Type[BaseModel] = SearchProductsInput

    class Config:
        arbitrary_types_allowed = True

    def _execute(self, sortby: str = None, output: List[str] = None, title: str = None, product_type: str = None, vendor: str = None) -> List[Tuple[int, str]]:
        """
        Execute the search products tool.

        Args:
            title (str, optional): Title of the products to search for.
            product_type (str, optional): Product type to filter the search.
            vendor (str, optional): Vendor to filter the search.

        Returns:
            List[Tuple[int, str]]: List of products that match the search criteria.
        """
        try:
            logger.info("Executing the SearchProductsTool...")
            lowercase_title = title.casefold() if title is not None else None
            lowercase_product_type = product_type.strip().casefold() if product_type else None
            lowercase_vendor = vendor.strip().casefold() if vendor else None
            matching_products = []

            if output is None:
                output = ['Product ID', 'Title', 'Price']

            if sortby is None:
                sortby = 'default'

            # Set the initial values for pagination
            get_next_page = True
            limit = 100
            since_id = 0

            while get_next_page:
                logger.info("Fetching products from Shopify API...")
                logger.info(f"title: {title}")
                logger.info(f"product_type: {product_type}")
                logger.info(f"vendor: {vendor}")
                # Retrieve the products using the Shopify API with pagination parameters
                products = shopify.Product.find(limit=limit, since_id=since_id)

                for product in products:
                    if (not lowercase_title or lowercase_title in product.title.casefold()) and \
                        (not lowercase_product_type or lowercase_product_type in product.product_type.casefold()) and \
                            (not lowercase_vendor or lowercase_vendor in product.vendor.casefold()):
                        matching_products.append((product.id, product.title))

                # Check if there are more pages of results
                if len(products) < limit:
                    get_next_page = False
                else:
                    since_id = products[-1].id

            pretty_product_info = self._pretty_product_info(
                matching_products, output, sortby)
    
            logger.info(f"Found {len(products)} products.")
            return pretty_product_info
        except Exception as e:
            # Log the error using the logger
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)

            # Raise a ValueError with a custom error message
            raise ValueError(
                "An unexpected error occurred. Please check the logs for more details.")
    
    def _init_shopify(self):
        shop_config = ShopifyConfig()
        return shop_config.get_shop()

    def _generate_product_details(self, product, output):
        info = {}
        # convert all output fields to lowercase for case-insensitive comparison
        # replace space with underscore
        output = [o.replace(' ', '_').lower() for o in output]

        for field in output:
            if field == 'product_id':
                info[field] = getattr(product, 'id', 'N/A')
            elif field == 'title':
                info[field] = getattr(product, 'title', 'N/A')
            elif field == 'price':
                if hasattr(product, 'variants') and product.variants:
                    info[field] = product.variants[0].price
                else:
                    info[field] = "N/A"
            else:
                logger.info(
                    f"Product {product.id} doesn't have field {field}.")
                print(f"Product {product.id} doesn't have field {field}.")

        return info

    def _pretty_product_info(self, matching_products: List[Dict], output: List[str], sortby: str):
        product_info_list = []
        pretty_product_info = ""

        for product in matching_products:
            # generate product details directly
            info = self._generate_product_details(product, output)
            product_info_list.append(info)

        # Apply sorting
        if sortby != "default":
            field, direction = sortby.split('-')
            reverse = direction == 'desc'
            if field == 'alpha':
                product_info_list.sort(
                    key=lambda x: x.get('title', ""), reverse=reverse)
            elif field == 'price':
                product_info_list.sort(
                    key=lambda x: float(
                        x.get('price', 0)), reverse=reverse)
            else:
                product_info_list.sort(
                    key=lambda x: x.get(field, ""), reverse=reverse)

        # Prepare the table
        # Mapping from field keys to headers
        field_to_header = {
            "product_id": "Product ID",
            "title": "Title",
            "price": "Price"
        }

        # Convert the keys in the first dict in product_info_list to their actual versions
        headers = [field_to_header.get(key, key)
                for key in product_info_list[0].keys()]

        # Convert the dictionaries in product_info_list to lists
        product_info_list = [list(d.values()) for d in product_info_list]

        # Now pass headers to tabulate()
        table = tabulate(product_info_list, headers=headers, tablefmt="pretty")
        table = table.replace(" ", "\u00A0")
        pretty_product_info = f"Found {len(matching_products)} products:\n{table}"

        return pretty_product_info
