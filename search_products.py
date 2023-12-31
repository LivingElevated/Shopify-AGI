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
    tags: Optional[str] = Field(
        None,
        description="Vendor to filter the search."
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

    def _execute(self, title: Optional[str] = None, product_type: Optional[str] = None, vendor: Optional[str] = None, tags: Optional[str] = None) -> List[Tuple[int, str]]:
        """
        Execute the search products tool.

        Args:
            title (str, optional): Title of the products to search for.
            product_type (str, optional): Product type to filter the search.
            vendor (str, optional): Vendor to filter the search.

        Returns:
            List[Tuple[int, str]]: List of products that match the search criteria.
        """
        # Validate input parameters
        if title is None and product_type is None and vendor is None and tags is None:
            print(
                "At least one search parameter (title, product_type, or vendor) must be provided.")
            raise ValueError(
                "At least one search parameter (title, product_type, or vendor) must be provided.")

        lowercase_title = title.lower() if title else None
        lowercase_product_type = product_type.lower() if product_type else None
        lowercase_vendor = vendor.lower() if vendor else None

        # Convert tags to a list
        if tags:
            lowercase_tags = [tag.strip() for tag in tags.split(",")]
        else:
            lowercase_tags = None

        matching_products = []

        output = ['Product ID', 'Title', 'Price']

        sortby = 'default'

        shop = self._init_shopify()
        products = self._get_all_products(shop, sortby)

        # Filter the products based on the search criteria
        for product in products:
            if (
                (not lowercase_title or lowercase_title in product.title.lower()) and
                (not lowercase_product_type or lowercase_product_type in product.product_type.lower()) and
                (not lowercase_vendor or lowercase_vendor in product.vendor.lower()) and
                # Check if all tags are present
                (not lowercase_tags or all(
                    tag in product.tags.lower() for tag in lowercase_tags))
                     ):
                matching_products.append(product)

        pretty_product_info = self._pretty_product_info(
            matching_products, output, sortby)

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
