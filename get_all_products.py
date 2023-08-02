import shopify
from tabulate import tabulate
from typing import Type, Union, Dict, Any, List, Optional, Tuple

from pydantic import BaseModel, Field, root_validator


# Local application/library specific imports
from superagi.tools.base_tool import BaseTool
from superagi.llms.base_llm import BaseLlm
from superagi.resource_manager.file_manager import FileManager
from superagi.lib.logger import logger
from superagi.tools.tool_response_query_manager import ToolResponseQueryManager

# Local shopify specific imports
from shopify_llm import LLMInput, ShopifyLLM
from shopify_config import ShopifyConfig


class GetAllSort(BaseModel):
    sortby: Optional[str] = Field(
        None, description="Sort method to use (use default if nothing is specified): default, alpha-asc, alpha-desc, price-asc, price-desc")
    output: Optional[List[str]] = Field(
        None, description="Output to be returned by tool. Default is Product ID, Title, Price.")


class GetAllProductsTool(BaseTool):
    """
    Get All Products Tool;          ;          
    Attributes:
        name : The name of the tool.
        description : The description of the tool.
        args_schema : The args schema.
    """
    name = "Get All Products"
    description = (
        "Fetch all products from Shopify with specified details and sort order. "
        "Default output is Product ID, Title, Price. Default sort order is by product ID. "
        "Sort order options are: default, alpha-asc, alpha-desc, price-asc, price-desc. "
        "alpha-asc: Alphabetically, in ascending order(A - Z). "
        "alpha-desc: Alphabetically, in descending order(Z - A). "
        "best-selling: By best-selling products. "
        "created: By date created, in ascending order(oldest - newest). "
        "created-desc: By date created, in descending order(newest - oldest). "
        "manual: In the order set manually by the shop owner."
        "price-asc: By price, in ascending order(lowest - highest)."
        "price-desc: By price, in descending order(highest - lowest)."
    )
    args_schema: Type[BaseModel] = GetAllSort

    class Config:
        arbitrary_types_allowed = True

    def _execute(self, sortby: str = None, output: List[str] = None):
        """
        Execute the get all products tool.
        Args:
            sortby : The Shopify sort method to use.
            output : The output fields to be returned by the tool.
        Returns:
            A string containing a pretty output of product details.
        """
        if output is None:
            output = ['Product ID', 'Title', 'Price']

        if sortby is None:
            sortby = 'default'

        shop = self._init_shopify()
        products = self._get_all_products(shop, sortby)
        pretty_product_info = self._pretty_product_info(products, output, sortby)

        logger.info(f"Found {len(products)} products.")
        return pretty_product_info

    def _init_shopify(self):
        shop_config = ShopifyConfig()
        return shop_config.get_shop()

    def _get_all_products(self, shop, sortby):
        limit = 100
        get_next_page = True
        since_id = 0
        products = []

        while get_next_page:
            products_page = shopify.Product.find(
                since_id=since_id, limit=limit)
            products.extend(products_page)

            if len(products_page) < limit:
                get_next_page = False
            else:
                since_id = products_page[-1].id

        return products

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
                if product.variants and hasattr(product.variants[0], 'price'):
                    info[field] = product.variants[0].price
                else:
                    info[field] = "N/A"
            else:
                logger.info(
                    f"Product {product.id} doesn't have field {field}.")
                print(f"Product {product.id} doesn't have field {field}.")

        return info

    def _pretty_product_info(self, products: List[Dict], output: List[str], sortby: str):
        product_info_list = []
        pretty_product_info = ""

        for product in products:
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
        pretty_product_info = f"Found {len(products)} products:\n{table}"

        return pretty_product_info
