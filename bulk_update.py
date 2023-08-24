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
from update_product import UpdateProductTool 


class BulkUpdateProductsInput(BaseModel):
    search_criteria: dict = Field(
        ...,
        description="Dictionary of key-value pairs for filtering products. Keys can be 'title', 'product_type', 'vendor', or 'tags'."
    )
    generate_price: bool = Field(
        False,
        description="Whether to generate a new price for the products."
    )
    generate_title: bool = Field(
        False,
        description="Whether to generate a new title for the products."
    )
    generate_description: bool = Field(
        False,
        description="Whether to generate a new description for the products."
    )
    generate_product_type: bool = Field(
        False,
        description="Whether to generate a new product type for the products."
    )
    generate_vendor: bool = Field(
        False,
        description="Whether to generate a new vendor for the products."
    )
    generate_tags: bool = Field(
        False,
        description="Whether to generate new tags for the products."
    )
    title: Optional[str] = Field(
        None,
        description="New title to update the products with."
    )
    description: Optional[str] = Field(
        None,
        description="New description to update the products with."
    )
    product_type: Optional[str] = Field(
        None,
        description="New product type to update the products with."
    )
    vendor: Optional[str] = Field(
        None,
        description="New vendor to update the products with."
    )
    tags: Optional[str] = Field(
        None,
        description="New tags to update the products with."
    )
    price: Optional[str] = Field(
        None,
        description="New price to update the products with."
    )
    context: Optional[str] = Field(
        None,
        description="Additional context or information."
    )


class BulkUpdateProductsTool(BaseTool):
    """
    Search And Update Product Tool is used to update  products on Shopify.
    Attributes:
        llm: Language Learning Model used for the tool.
        name : The name of the tool.
        description : The description of the tool.
        args_schema : The arguments schema.
        goals : The goals.
        resource_manager: Manages the file resources.
        permission_required: Specifies whether permission is required.
        tool_response_manager: Manages the responses from the tool.
    """
    llm: Optional[BaseLlm] = None
    agent_id: int = None
    name = "Bulk Update Products"
    description = (
        "This tool facilitates searching products in Shopify based on various criteria and updating products all of them. "
        "It generates detailed product descriptions, suitable prices, product types, and vendors "
        "using an AI model. The tool also saves this AI-generated information as metafields to the product."
    )
    args_schema: Type[BaseModel] = BulkUpdateProductsInput
    goals: List[str] = []
    permission_required: bool = True
    resource_manager: Optional[FileManager] = None
    tool_response_manager: Optional[ToolResponseQueryManager] = None

    class Config:
        arbitrary_types_allowed = True

    def _execute(
            self,
            search_criteria: dict,
            generate_price: bool = False,
            generate_title: bool = False,
            generate_description: bool = False,
            generate_product_type: bool = False,
            generate_vendor: bool = False,
            generate_tags: bool = False,
            title: Optional[str] = None,
            description: Optional[str] = None,
            product_type: Optional[str] = None,
            vendor: Optional[str] = None,
            tags: Optional[str] = None,
            price: Optional[str] = None,
            context: Optional[str] = None
            ) -> List[Tuple[int, str]]:
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
        if not search_criteria:
            print("Search criteria must be provided.")
            print(
                "At least one search parameter (title, product_type, or vendor) must be provided.")
            raise ValueError("Search criteria must be provided."
                             "At least one search parameter (title, product_type, or vendor) must be provided.")

        # Convert the search criteria to lowercase with conditional checks
        lowercase_title = search_criteria['title'].lower(
        ) if 'title' in search_criteria else None
        lowercase_product_type = search_criteria['product_type'].lower(
        ) if 'product_type' in search_criteria else None
        lowercase_vendor = search_criteria['vendor'].lower(
        ) if 'vendor' in search_criteria else None


        # Convert tags to a list
        if 'tags' in search_criteria:
            lowercase_tags = [tag.strip().lower()
                              for tag in search_criteria['tags'].split(",")]
        else:
            lowercase_tags = None

        # Initialize a list to store matching products
        matching_products = []
        # Initialize a list to store changes for each product
        product_changes = []

        # Instantiate the UpdateProductTool class
        update_tool = UpdateProductTool()

        shop = self._init_shopify()
        products = self._get_all_products(shop)

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
        # Filter the products based on the search criteria
        for product in matching_products:
            # Collect old details before updating
            old_title = product.title
            old_description = self.html_to_plain_text(product.body_html)
            old_product_type = product.product_type
            old_vendor = product.vendor
            old_tags = product.tags
            old_price = product.variants[0].price if product.variants else None

            # Update the product based on generate flags and new values
            update_tool._execute(
                product.id,
                generate_price=generate_price,
                generate_title=generate_title,
                generate_description=generate_description,
                generate_product_type=generate_product_type,
                generate_vendor=generate_vendor,
                generate_tags=generate_tags,
                title=title,
                description=description,
                product_type=product_type,
                vendor=vendor,
                tags=tags,
                price=price,
                context=context
            )

            # Collect new details after updating
            new_title = product.title
            new_description = self.html_to_plain_text(product.body_html)
            new_product_type = product.product_type
            new_vendor = product.vendor
            new_tags = product.tags
            new_price = product.variants[0].price if product.variants else None

            # Check if any information has been updated
            has_changes = (
                old_title != new_title or
                old_description != new_description or
                old_product_type != new_product_type or
                old_vendor != new_vendor or
                old_tags != new_tags or
                old_price != new_price
            )

            # Append changes to the list if there are any
            if has_changes:
                product_changes.append(
                    (product.id, old_title, new_title, old_description, new_description,
                     old_product_type, new_product_type, old_vendor, new_vendor,
                     old_tags, new_tags, old_price, new_price)
                )

        # Create a table to display the changes
        if product_changes:
            table_headers = ["Product ID", "Old Title", "New Title", "Old Description", "New Description",
                             "Old Product Type", "New Product Type", "Old Vendor", "New Vendor",
                             "Old Tags", "New Tags", "Old Price", "New Price"]
            changes_table = tabulate(product_changes, headers=table_headers)

            print(changes_table)
            updated_table = f"Updated {len(matching_products)} products:\n{changes_table}"
        else:
            print("No updates were made.")
            updated_table = f"No updates were made."

        logger.info(f"Found {len(products)} products.")
        return updated_table

    def _init_shopify(self):
        shop_config = ShopifyConfig()
        return shop_config.get_shop()

    def _get_all_products(self, shop):
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
