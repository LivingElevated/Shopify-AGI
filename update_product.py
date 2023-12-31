import shopify
import re
import json
from textwrap import dedent
from typing import Type, Union, Dict, Any, List, Optional, Tuple

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Local application/library specific imports
from superagi.tools.base_tool import BaseTool
from superagi.llms.base_llm import BaseLlm
from superagi.resource_manager.file_manager import FileManager
from superagi.lib.logger import logger
from superagi.tools.tool_response_query_manager import ToolResponseQueryManager

# Local shopify specific imports
from shopify_llm import LLMInput, ShopifyLLM
from shopify_config import ShopifyConfig


class UpdateProductInput(BaseModel):
    generate_title: bool = Field(
        False,
        description="If True, generate the title based on the old product details. If False, use the provided title.",
    )
    generate_description: bool = Field(
        False,
        description="If True, generate the description based on the old product details. If False, use the provided description.",
    )
    generate_product_type: bool = Field(
        False,
        description="If True, generate the product type based on the old product details. If False, use the provided product type.",
    )
    generate_vendor: bool = Field(
        False,
        description="If True, generate the vendor based on the old product details. If False, use the provided vendor.",
    )
    generate_tags: bool = Field(
        False,
        description="If True, generate the tags based on the old product details. If False, use the provided tags.",
    )
    generate_price: bool = Field(
        False,
        description="If True, generate the price based on the old product details. If False, use the provided price.",
    )

    product_id: str = Field(
        ...,
        description="The ID of the product to update."
    )
    title: Optional[str] = Field(
        None, 
        description="Updated Title of the product."
        )
    description: Optional[str] = Field(
        None, 
        description="Updated description of the product."
        )
    product_type: Optional[str] = Field(
        None, 
        description="Updated Type of the product."
        )
    vendor: Optional[str] = Field(
        None, 
        description="Updated Vendor of the product."
        )
    tags: Optional[str] = Field(
        None,
        description="Updated Tags for the product."
    )
    price: Optional[str] = Field(
        None, 
        description="Updated Price of the product."
        )
    context: Optional[str] = Field(
        None,
        description="Optional context for the product. (ie. store name, theme, ect.) This will be used to generate AI-generated fields."
    )


class UpdateProductTool(BaseTool):
    """
    Update Product Tool is used to update  products on Shopify.
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
    name = "Update Product"
    description = (
        "This tool facilitates updating products on Shopify. "
        "It generates detailed product descriptions, suitable prices, product types, and vendors "
        "using an AI model. The tool also saves this AI-generated information as metafields to the product."
    )
    args_schema: Type[BaseModel] = UpdateProductInput
    goals: List[str] = []
    permission_required: bool = True
    resource_manager: Optional[FileManager] = None
    tool_response_manager: Optional[ToolResponseQueryManager] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, llm: Optional[BaseLlm] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default to ThinkingTool if not provided
        self.llm = llm if llm else ShopifyLLM()

    def validate_field(self, value: Any, max_length: int, field_name: str, field_type: str = "string", required: bool = False) -> Any:
        """
        Validate a field.
        Args:
            value : The value.
            max_length : The max length.
            field_name : The field name.
            field_type : The field type.
            required : If the field is required.
        Returns:
            The validated field.
        """

        try:
            if required and not value:
                raise ValueError(f"{field_name}::\"{value}\" is required.")

            if value:
                if field_type == "string":
                    if not isinstance(value, str):
                        raise ValueError(
                            f"{field_name}::\"{value}\" must be a string.")
                    if not re.match("^[a-zA-Z0-9\s\-.,!?'\";:/]*$", value):
                        raise ValueError(
                            f"{field_name}::\"{value}\" contains inappropriate characters.")
                    if len(value) > max_length:
                        raise ValueError(
                            f"{field_name}::\"{value}\" is too long.")
                elif field_type == "html":
                    # Validate HTML here. You could use a library like BeautifulSoup to help.
                    if not isinstance(value, str):
                        raise ValueError(
                            f"{field_name}::\"{value}\" must be a string.")
                    soup = BeautifulSoup(value, "html.parser")
                    text_content = soup.get_text(strip=True)
                    if not text_content:  # This checks if the HTML has any content
                        raise ValueError(
                            f"{field_name}::\"{value}\" must contain text.")
                    if len(text_content) > max_length:  # Check length of the extracted text
                        raise ValueError(f"{field_name}::\"{value}\" is too long.")
                elif field_type == "price":
                    try:
                        value = float(value)
                    except ValueError:
                        raise ValueError(
                            f"{field_name}::\"{value}\" must be a float.")
                    if value < 0:
                        raise ValueError(
                            f"{field_name}::\"{value}\" must be non-negative.")
                
        except ValueError as e:
            logger.warning(f"ValueError in validate_field: {e}")
            raise  # re-raise the exception after logging

        return value

    def generate_info(self, task_description: str) -> str:
        """
        Generate product information using Language Learning Model.

        Args:
            task_description (str): The task description.

        Returns:
            str: The generated information.

        Raises:
            ValueError: If LLM instance is None or AI fails to generate information.
        """
        logger.debug("(generate_info) LLM Instance: %s", self.llm)
        logger.debug(type(self.llm))

        try:
            logger.info("Generating product information...")
            # Initialize the tool.
            thinking_tool = ShopifyLLM(llm=self.llm)

            if thinking_tool.llm is None:
                raise ValueError(
                    "LLM instance is None. Please ensure it is properly initialized in ShopifyLLM.")

            llm_input = LLMInput(task_description=task_description)
            generated_info = thinking_tool._execute(**llm_input.dict())
            if not generated_info:
                raise ValueError(
                    f"AI failed to generate information for task: {task_description}")
            
        except ValueError as e:
            logger.error(f"ValueError in generate_info: {e}")
            raise
        
        logger.info(generated_info)
        return generated_info
    

    def _generate_value_based_on_flag(self, generate_flag: bool, old_value: str, new_value: Optional[str], task_description: str = None, context: str = None) -> Any:
        if generate_flag and task_description:
            # Combine task description and context for more informative message
            if context:
                task_description = f"Use the context of '{context}' to: {task_description}"
            else:
                task_description = task_description
            # Generate new value based on combined description, old value, and possibly new value
            print(task_description)
            return self.generate_info(task_description)
        elif generate_flag:
            # Handle cases where task description is missing
            logger.warning(
                "Task description is missing for generating new value.")
            return new_value if new_value is not None else old_value
        else:
            return new_value if new_value is not None else old_value
        

    def _generate_price_based_on_flag(self, generate_flag: bool, old_value: str, new_value: str, product, title, description, product_type, tags, context) -> Tuple[str, Optional[str]]:
        print("Title:", title)
        print("Description:", description)
        print("Product Type:", product_type)
        print("Tags:", tags)

        if not title and product:
            title = product.title
        if not description and product:
            description = product.body_html
        if not product_type and product:
            product_type = product.product_type
        if not tags and product:
            tags = product.tags

        print("Title:", title)
        print("Description:", description)
        print("Product Type:", product_type)
        print("Tags:", tags)
        
        if new_value:
            price_data = new_value
        else:
            price_data = old_value

        if generate_flag:
            price, price_metadata = self._generate_specific_price(
                title, description, product_type, tags, price_data, context)
            return price, price_metadata
        elif new_value:
            return new_value, None
        else:
            return old_value, None

    def _generate_vendor_based_on_flag(self, generate_flag: bool, old_value: str, new_value: str, product, title, description, product_type, tags, price, context) -> Tuple[str, Optional[str]]:
        print("Title:", title)
        print("Description:", description)
        print("Product Type:", product_type)
        print("Tags:", tags)
        print("Price:", price)

        if not title and product:
            title = product.title
        if not description and product:
            description = product.body_html
        if not product_type and product:
            product_type = product.product_type
        if not price and product:
            price = product.price
        if not tags and product:
            tags = product.tags

        print("Title:", title)
        print("Description:", description)
        print("Product Type:", product_type)
        print("Tags:", tags)
        print("Price:", price)

        
        if new_value:
            vendor_data = new_value
        else:
            vendor_data = old_value
        
        if generate_flag:
            vendor, vendor_metadata = self._generate_specific_vendor(
                title, description, product_type, tags, price, vendor_data, context)
            return vendor, vendor_metadata
        elif new_value:
            return new_value, None
        else:
            return old_value, None
        
    def trim_product_type(self, product_type: str, max_length: int) -> Tuple[str, Optional[str]]:
        """
        Trim the product_type string to the maximum length and return the original product_type if it exceeded max_length.

        This function checks if the product_type string length exceeds the maximum length.
        If so, it trims the product_type to the maximum length and keeps the original product_type as metadata.

        Returns a tuple with two strings. The first string contains the trimmed product_type.
        The second string contains the original product_type if it was trimmed, or None if it was not.
        """

        # Check if product_type is a string
        if not isinstance(product_type, str):
            logger.error("product_type must be a string")
            raise ValueError("product_type must be a string")

        if len(product_type) > max_length:
            return product_type[:max_length], product_type
        else:
            return product_type, None

    def trim_tags(self, tags_string: str, max_length: int) -> Tuple[str, Optional[str]]:
        """
        Trim the tags string to the maximum length and return any overflow tags.

        This function splits the tags string into individual tags, keeps only as many
        tags as will fit within the length limit, and then joins them back together
        into a string. If a tag would be partially included (which would make it
        incomplete), it gets dropped.

        Returns a tuple with two strings. The first string contains the trimmed tags.
        The second string contains the overflow tags that were removed, or None if
        there were no overflow tags.
        """

        # Check if tags_string is a string
        if not isinstance(tags_string, str):
            logger.error("tags_string must be a string")
            raise ValueError("tags_string must be a string")
        
        tags_list = tags_string.split(
            '\n')  # Split the tags string into individual tags
        # Remove leading numbers and trailing periods
        tags_list = [re.sub(r'^\d+\.\s|\.$', '', tag) for tag in tags_list]

        tags = []  # Create an empty list to hold the trimmed tags
        tags_metadata = []  # Create an empty list to hold any overflow tags
        length = 0  # Keep track of the total length of the tags

        # Iterate over the tags
        for tag in tags_list:
            tag = tag.strip()
            # Calculate new length including this tag and a comma and space for all but the first tag
            new_length = len(tag) + length + (2 * (length > 0))
            # If adding this tag would exceed the maximum length, add to overflow list
            if new_length > max_length:
                tags_metadata.append(tag)
                continue
            # Otherwise, add the tag to the list and update the length
            tags.append(tag)
            length = new_length

        # Join the tags back together into a string
        tags = ', '.join(tags)
        tags_metadata = ', '.join(tags_metadata) if tags_metadata else None

        return tags, tags_metadata

    def _generate_specific_price(self, title, description, product_type, tags, price_data ,context) -> Tuple[str, Optional[str]]:
        """
        Generate a specific price for a product.

        Args:
            title (str): The title of the product.
            description (str, optional): The description of the product. Defaults to None.
            product_type (str, optional): The type of the product. Defaults to None.
            tags (str, optional): The tags associated with the product. Defaults to None.

        Returns:
            Tuple[str, Optional[str]]: Tuple containing the generated price and metadata (only if there were multiple prices, the response was too long, had a space or contained more than 5 words).
        """
        print("Generating a specific price...")
        print("Title:", title)
        print("Description:", description)
        print("Product Type:", product_type)
        print("Tags:", tags)

        price_prompt = f"Suggest a suitable price for a product with title: {title}, description: {description}, type: {product_type}, and tags: {tags}."

        if price_data:
            context_details = f"Use the context of: {context} and the previous/provided pricing data: {price_data} to:"
        else:
            context_details = f"Use the context of: {context} to:"

        # Combine context_details and vendor_prompt
        task_description = f"{context_details} {price_prompt}"
        print(task_description)
        
        price = self.generate_info(task_description)

        price_metadata = None
        # if there are multiple prices or the response is too long or has a space
        if "-" in price or "," in price or " " in price or len(price.split()) > 5:
            price_metadata = price  # save the unsuitable price as metadata
            # Extract price range and calculate average
            price_range = re.findall(r"\b\d+\b", price)
            if price_range and len(price_range) == 2:
                price = str((float(price_range[0]) + float(price_range[1])) / 2)
            else:
                specific_price = f"Based on the previous information, {price}, select a specific price that we should start selling our product at. (Please reply in a single specific numeric value only.)"
                print(specific_price)
                # Generate a specific price
                price = self.generate_info(specific_price)

        # convert price to float
        price = float(price.replace("$", ""))

        return price, price_metadata
    
    def _generate_specific_vendor(self, title, description, product_type, tags, price, vendor_data, context) -> Tuple[str, Optional[str]]:
        """
        Generate a specific vendor for a product based on title, description, product_type, price, and tags.

        Args:
            title (str): The title of the product.
            description (Optional[str], optional): The description of the product. Defaults to None.
            product_type (Optional[str], optional): The product type. Defaults to None.
            tags (Optional[str], optional): The tags related to the product. Defaults to None.
            price (Optional[str], optional): The price of the product. Defaults to None.

        Returns:
            Tuple[str, Optional[str]]: A tuple containing the generated vendor and any vendor metadata (None if not applicable).
        """
        print("Generating a specific vendor...")
        print("Title:", title)
        print("Description:", description)
        print("Product Type:", product_type)
        print("Tags:", tags)
        print("Price:", price)
        print("Vendor Data:", vendor_data)


        # Prepare the prompt string with available fields
        prompt_parts = {"title": title, "description": description,
                        "type": product_type, "price": price, "tags": tags}

        vendor_prompt = "Suggest a suitable vendor for a product with "

        if vendor_data:
            context_details = f"Use the context of: {context} and the previous/provided vendor data: {vendor_data} to:"
        else:
            context_details = f"Use the context of '{context}' to:"

        for name, value in prompt_parts.items():
            if value is not None:  # If value exists, include it in the prompt
                if not isinstance(value, str):  # If value is not a string, convert it
                    value = str(value)
                vendor_prompt += f"{name}: {value}, "

        # Remove the last comma and add a period
        vendor_prompt = vendor_prompt.rstrip(", ") + "."

        # Combine context_details and vendor_prompt
        task_description = f"{context_details} {vendor_prompt}"
        print(task_description)

        vendor = self.generate_info(task_description)

        vendor_metadata = None
        # if there are multiple vendors or the response is too long
        if "," in vendor or len(vendor.split()) > 5:
            vendor_metadata = vendor  # save the unsuitable vendor as metadata
            # Generate a specific vendor
            specific_vendor = f"Based on the previous information, {vendor}, select a specific vendor that we should use for our product. (Please reply with no context or details other than the vendor choosen.)"
            print(specific_vendor)
            vendor = self.generate_info(specific_vendor)

        return vendor, vendor_metadata
    

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
    
    def generate_title_task_description(self, product, title, product_type, vendor) -> str:
        if not product_type and product:
            product_type = product.product_type
        if not vendor and product:
            vendor = product.vendor

        context_details = [
            f"Existing Title: {product.title}" if product.title else None,
            f"Product Type: {product_type}" if product_type else None,
            f"Vendor: {vendor}" if vendor else None,
            f"Existing Description: {self.html_to_plain_text(product.body_html)}" if product.body_html else None
        ]

        context_details_str = ', '.join(
            [detail for detail in context_details if detail is not None])

        if title:  # If both description and product type are provided
            task_description = (
                f"Generate a catchy product title based on the provided title '{title}'. "
                f"Product context details: {context_details_str}."
            )
        else:  # If there's no provided title, generate a catchy product title based on the existing title
            task_description = (
                f"Generate a catchy product title based on the existing title '{product.title}'. "
                f"Product context details: {context_details_str}."
            )

        return task_description

    def generate_description_task_description(self, product, title, description, product_type, vendor, tags, price) -> str:
        if not title and product:
            title = product.title
        if not product_type and product:
            product_type = product.product_type
        if not vendor and product:
            vendor = product.vendor
        if not tags and product:
            tags = product.tags
        if not price and product:
            price = product.price

        context_details = [
            f"Title: {title}" if title else None,
            f"Existing Description: {self.html_to_plain_text(product.body_html)}" if product.body_html else None,
            f"Product Type: {product_type}" if product_type else None,
            f"Vendor: {vendor}" if vendor else None,
            f"Tags: {tags}" if tags else None,
            f"Price: {price}" if price else None
        ]

        context_details_str = ', '.join(
            [detail for detail in context_details if detail is not None])

        if description:
            task_description = (
                f"Write a captivating product description (between 1500 and 5000 characters) based on the provided description '{description}'. "
                f"Product context details: {context_details_str}."
            )
        else:
            task_description = (
                f"Write a captivating product description (between 1500 and 5000 characters) based on the existing description. "
                f"Product context details: {context_details_str}."
            )

        return task_description

    def generate_product_type_task_description(self, product, title, description, product_type, vendor, tags, price) -> str:
        if not title and product:
            title = product.title
        if not description and product:
            description = product.body_html
        if not vendor and product:
            vendor = product.vendor
        if not tags and product:
            tags = product.tags
        if not price and product:
            price = product.price

        context_details = [
            f"Title: {title}" if title else None,
            f"Description: {description}" if description else None,
            f"Existing Product Type: {product.product_type}" if product.product_type else None,
            f"Vendor: {vendor}" if vendor else None,
            f"Tags: {tags}" if tags else None,
            f"Price: {price}" if price else None
        ]

        context_details_str = ', '.join(
            [detail for detail in context_details if detail is not None])

        if product_type:
            task_description = (
                f"Suggest a suitable product type based on the provided product type '{product_type}'. "
                f"Product context details: {context_details_str}."
            )
        else:
            task_description = (
                f"Suggest a suitable product type based on the existing product type '{product.product_type}'. "
                f"Product context details: {context_details_str}."
            )

        return task_description

    def generate_tags_task_description(self, product, title, description, product_type, vendor, tags, price) -> str:
        if not title and product:
            title = product.title
        if not description and product:
            description = product.body_html
        if not product_type and product:
            product_type = product.product_type
        if not vendor and product:
            vendor = product.vendor
        if not price and product:
            price = product.price

        context_details = [
            f"Title: {title}" if title else None,
            f"Description: {description}" if description else None,
            f"Existing Tags: {product.tags}" if product.tags else None,
            f"Product Type: {product_type}" if product_type else None,
            f"Vendor: {vendor}" if vendor else None,
            f"Price: {price}" if price else None
        ]

        context_details_str = ', '.join(
            [detail for detail in context_details if detail is not None])

        if tags:
            task_description = (
                f"Generate tags based on the provided tags '{tags}'. "
                f"Product context details: {context_details_str}."
            )
        else:
            task_description = (
                f"Generate tags based on the existing tags '{product.tags}'. "
                f"Product context details: {context_details_str}."
            )

        return task_description
    
    def _init_shopify(self):
        shop_config = ShopifyConfig()
        return shop_config.get_shop()

    def _execute(
        self,
        product_id: str,
        generate_price: bool=False,
        generate_title: bool=False,
        generate_description: bool=False,
        generate_product_type: bool=False,
        generate_vendor: bool=False,
        generate_tags: bool=False,
        title: Optional[str]=None,
        description: Optional[str]=None,
        product_type: Optional[str]=None,
        vendor: Optional[str]=None,
        tags: Optional[str]=None,
        price: Optional[str]=None,
        context: Optional[str]=None
    ) -> Optional[shopify.Product]:
        """Update a product on Shopify.

        Args:
            generate_title (bool): Whether to generate the title.
            generate_description (bool): Whether to generate the description.
            generate_product_type (bool): Whether to generate the product type.
            generate_vendor (bool): Whether to generate the vendor.
            generate_tags (bool): Whether to generate the tags.
            generate_price (bool): Whether to generate the price.
            product_id (str): The ID of the product to update.
            title (Optional[str], optional): The new title of the product. Defaults to None.
            description (Optional[str], optional): The new description of the product. Defaults to None.
            product_type (Optional[str], optional): The new product type. Defaults to None.
            vendor (Optional[str], optional): The new vendor. Defaults to None.
            tags (Optional[str], optional): The new tags for the product. Defaults to None.
            price (Optional[str], optional): The new price. Defaults to None.
            context (Optional[str], optional): Optional context for the product. Defaults to None.

        Returns:
            Optional[shopify.Product]: The updated product if successful, or None if there was an error.
        """

        # Initialize Shopify API
        shop = self._init_shopify()
        product = shopify.Product.find(product_id)

        # Initialize metadata
        vendor_metadata = None
        tags_metadata = None
        price_metadata = None
        type_metadata = None

        if not product:
            print(f"Product {product_id} not found.")
            return None
        
        # Define option_values to hold the new option values (if provided)
        option_values = None  # Initialize with None
        # Retrieve existing options and their values
        existing_options = product.options
        existing_option_values = {
            option.name: option.values  # Assuming option.values is a list of strings
            for option in existing_options
        }

        if product:
            old_product_details = self._generate_product_details(
                            product)
            self._log_product_details(old_product_details)
            file_name = f"Product ID {product_id}.csv"
            # Write backup of old product details to a file
            self.resource_manager.write_file(file_name, old_product_details)

            if title or generate_title:
                print("Updating title...")
                ...
                print("Existing Title:", product.title)
                print("New Title:", title)

                # Handle each product input value based on the boolean flags
                title = self._generate_value_based_on_flag(
                    generate_title, product.title, title,
                    self.generate_title_task_description(
                        product, title, product_type, vendor),
                    context
                )
                # List of small words to be in lowercase (customize it according to your needs)
                small_words = ['a', 'an', 'and', 'as', 'at', 'but', 'by', 'for',
                            'if', 'in', 'nor', 'of', 'on', 'or', 'so', 'the', 'to', 'up', 'yet']

                # Capitalize every word in the title
                title = title.title()

                # Lowercase small words (but not the first or the last word of the title)
                title_words = title.split()
                for i in range(1, len(title_words) - 1):  # skip the first and the last word
                    if title_words[i].lower() in small_words:
                        title_words[i] = title_words[i].lower()
                title = ' '.join(title_words)

                product.title = title
                print("Updated Title:", product.title)

            if description or generate_description:
                print("Updating description...")
                ...
                print("Existing Description:", product.body_html)
                print("New Description:", description)

                description = self._generate_value_based_on_flag(
                    generate_description, self.html_to_plain_text(
                        product.body_html), description,
                    self.generate_description_task_description(
                        product, title, description, product_type, vendor, tags, price),
                    context
                )

                description = "\n".join(
                    [line for line in description.split('\n') if line.strip()])
                # Convert to HTML by adding <p> tags for each paragraph
                description = '<p>' + description.replace('\n', '</p><p>') + '</p>'
                # Remove empty paragraphs
                description = re.sub(r'(</p><p>)+', '</p><p>', description)
                print("Updated Description:", description)

            if product_type or generate_product_type:
                print("Updating product type...")
                ...
                print("Existing Product Type:", product.product_type)
                print("New Product Type:", product_type)

                product_type = self._generate_value_based_on_flag(
                    generate_product_type, product.product_type, product_type,
                    self.generate_product_type_task_description(
                        product, title, description, product_type, vendor, tags, price),
                    context
                )

                max_length = 255
                if len(product_type) > max_length:  # Replace with the actual maximum length
                    product_type, type_metadata = self.trim_product_type(
                        product_type, max_length)
                print("Trimmed Product Type:", product_type)

            if tags or generate_tags:
                print("Updating tags...")
                ...
                print("Existing Tags:", product.tags)
                print("New Tags:", tags)

                tags = self._generate_value_based_on_flag(
                    generate_tags, product.tags, tags,
                    self.generate_tags_task_description(
                        product, title, description, product_type, vendor, tags, price),
                    context
                )
                tags, tags_metadata = self.trim_tags(tags, 255)
                print("Trimmed Tags:", tags)

            if price or generate_price:
                print("Updating price...")
                ...
                print("Existing Price:", product.variants[0].price if product.variants else None)
                print("New Price:", price)

                price, price_metadata = self._generate_price_based_on_flag(
                    generate_price,  # Generate flag
                    product.variants[0].price if product.variants else None,  # Old value
                    price,  # New value
                    product,  # Additional arguments
                    title,
                    description,
                    product_type,
                    tags,
                    context  
                )
                print("Updated Price:", price)

            if vendor or generate_vendor:
                print("Updating vendor...")
                ...
                print("Existing Vendor:", product.vendor)
                print("New Vendor:", vendor)

                vendor, vendor_metadata = self._generate_vendor_based_on_flag(
                    generate_vendor,    # Generate flag
                    product.vendor,  # Old value
                    vendor,  # New value
                    product,  # Additional arguments
                    title, 
                    description, 
                    product_type, 
                    tags, 
                    price, 
                    context
                    )
                print("Updated Vendor:", vendor)

        try:
            if description:
                print("Saving description...")
                product.body_html = self.validate_field(
                    description, 65535, "Description", field_type="html", required=True)
            if product_type:
                print("Saving product type...")
                product.product_type = self.validate_field(
                    product_type, 255, "Product type", required=True)
            if tags:
                print("Saving tags...")
                product.tags = self.validate_field(tags, 255, "Tags")
            if price:
                print("Saving price...")
                # Remove any non-numeric characters from the price
                price = re.sub(r'[^\d.]', '', price)

                # Update the price for each variant
                for variant in product.variants:
                    variant.price = self.validate_field(
                        price, 255, "Price", field_type="price", required=True)
            if vendor:
                print("Saving vendor...")
                product.vendor = self.validate_field(
                    vendor, 255, "Vendor", required=True)
            # Update options and values only if option_values are provided
            if option_values:
                    # Update product options and values
                    for option_name, option_values in existing_option_values.items():
                        # Find the option object by name
                        option = next(
                            (opt for opt in product.options if opt.name == option_name), None)
                        if option:
                            # Update option values if provided
                            if option_values:
                                option.values = [{'value': value}
                                                for value in option_values]
            # Print the data you're sending to the API just before making the request
            print("Data to be sent:", existing_option_values)

        except ValueError as e:
            try:
                field_name, value_and_error_message = str(e).split("::", 2)
                value, error_message = value_and_error_message.split(' ', 1)
                value = value.replace('"', '')  # remove the quotes around the value
            except ValueError:
                logger.error(f"Validation error: {e}")
                return f"Validation error: {e}"
            logger.error(
                f"Validation error in field '{field_name}' with value '{value}': {error_message}")
            return f"Validation error in field '{field_name}' with value '{value}': {error_message}"
        
        # Try to save the product, and handle any exceptions that might occur.
        try:
            success = product.save()
            print("Product saved:", success)

            if not success:
                error_messages = product.errors.full_messages()
                error_str = ', '.join(error_messages)
                logger.error(f"Failed to save product: {error_str}")
                return f"Failed to save product: {error_str}"
        except Exception as e:
            logger.error(e)
            return f"Error while saving product: {e}"

        # After product save
        if success:
            # Add AI-generated results as metadata
            ai_metadata = [
                "Product Type Information: " + type_metadata if type_metadata else None,
                "Vendor Information: " + vendor_metadata if vendor_metadata else None,
                "Additional Tags: " + tags_metadata if tags_metadata else None,
                "Pricing Information: " + price_metadata if price_metadata else None
            ]

            # Filter out None values
            ai_metadata = [entry for entry in ai_metadata if entry is not None]

            # Convert list into a multiline string
            ai_metadata_string = '\n\n'.join(ai_metadata)

            # Add metafield if there's at least one valid value
            if ai_metadata_string:
                metafield = shopify.Metafield()
                metafield.namespace = "ai_metadata"
                metafield.key = "ai_results"
                metafield.value = ai_metadata_string
                metafield.type = "multi_line_text_field"
                product.add_metafield(metafield)
                product.save()  # Save the product to commit the changes
                if not product.save():
                    logger.error("Failed to save metadata:")
                    for message in product.errors.full_messages():
                        logger.error("  " + message)


            # Compute the new lines outside of f-string
            metafields_values = ',\n'.join(
                [metafield.value for metafield in product.metafields()])
            # Send the product details to the tool response manager
            product_details_str = f"""
                Title: {product.title}

                Description: 
                {self.html_to_plain_text(product.body_html)}

                Product Type: {product.product_type}

                Vendor: {product.vendor}

                Tags:
                {product.tags}

                Price: {product.variants[0].price if product.variants else None}

                Product ID: {product.id}

                Product Metafields:
                {', '.join([str(metafield) for metafield in product.metafields()])}

                Metafields Values: 
                {metafields_values}
                """

        logger.info(product_details_str)

        update_message = dedent(f"""
                                    Successfully Updated Product ID: {product.id}
                                    Backup written to file: "{file_name}" in the current resource manager output directory.

                                    Updated Product Details:
                                    {product_details_str}
                                    
                                    """)

        return update_message

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
    
    def _log_product_details(self, product_details):
        logger.info(product_details)
