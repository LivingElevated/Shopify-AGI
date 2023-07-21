<p align=center>
<a href="https://superagi.co"><img src=https://superagi.co/wp-content/uploads/2023/05/SuperAGI_icon.png></a>
</p>

# SuperAGI Shopify Tool

The robust SuperAGI Shopify Tool lets help with their coding tasks like writing, reviewing, refactoring code, fixing bugs, and understanding programming concepts.

## 💡 Features
1. **Create Product:** With SuperAGI's Shopify Tool, creating products is a streamlined and effortless process, making your programming tasks much simpler.

2. **All Product Data:**

3. **Get All Products:** 

4. **Get Product:** 

## ⚙️ Installation

### 🛠 **Setting Up of SuperAGI**
**Step 1: Set up the SuperAGI**

Set up the SuperAGI by following the instructions given (https://github.com/TransformerOptimus/SuperAGI/blob/main/README.MD)

You'll be able to use the Shopify Tool on the fly once you have setup SuperAGI.

**Step 2: Installing Necessary APIs and Base Tool Classes via pip**

You'll need to install the required APIs and base tool-related classes to facilitate the integration of your tool with SuperAGI.

Use the following pip command (https://pypi.org/project/superagi-tools/) Run the following command in your terminal or command prompt:
```
pip install superagi-tools
```

Executing this command will install the necessary SuperAGI base tool and toolkit class.

**Step 3: Linking Your GitHub Repository to SuperAGI (Locally)**

Start SuperAGI using ```docker-compose up --build```

Next, you need to add your GitHub repository link to SuperAGI’s front end.

You can either click on the “add custom tool” link at home or navigate to the toolkits section. Paste your toolkit repository and save changes. The SuperAGI tool manager will take care of the installation of your tool along with its dependencies.


![FqqD51nbeyRIwypeMTAxrjVdQ0F2-2023-07-06T01-32-36 496Z-f2okb7z6m4arn79xeuqpdslc](https://github.com/LivingElevated/Shopify-AGI/assets/16730410/21e4c0e0-a256-494f-9708-468c661389f8)

Add Custom Tool

The GitHub link and toolkit name are stored in a superagi/tools/tools.json like this:
{ "toolkit-name": "YOUR-GITHUB-LINK" }

**Step 4: Re-build SuperAGI Using Docker and Start Using Your Tools**

Once the linking is completed, you have to restart your docker.

Run the following command in the terminal:

```
docker compose down docker compose up --build
```

This command restarts your docker, builds it again, and runs it.

During the Docker run, your tool’s dependencies (specified in requirements.txt) will be installed automatically on startup by a script install-tool-dependency.sh.

Now, you should be able to configure your tool settings from the toolkit section and start using them during the agent provisioning.

## Running SuperAGI Shopify Tool

You can simply ask your agent to read or go through your Shopify store, and it'll be able to do any shopify  admin features as mentioned above.
