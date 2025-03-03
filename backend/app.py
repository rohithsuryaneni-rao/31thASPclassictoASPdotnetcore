from flask import Flask, request, jsonify
import os
import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
from flask_cors import CORS
import ssl
import logging
import pyodbc
import re
from flask import send_file
import urllib.parse
from dotenv import load_dotenv
from langchain_community.llms import OpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
import warnings
import shutil
warnings.filterwarnings("ignore", category=DeprecationWarning)
 
# Load environment variables from .env
load_dotenv()
 
# Disable SSL verification warnings
ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings()
 
app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})
 # Configuration variables
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_API_KEY = os.getenv('AZURE_API_KEY')
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "ConvertedRepos")
GITHUB_API_BASE_URL = "https://api.github.com/repos"
MODEL = "gpt-4"
TIMEOUT = 300  # Increased timeout to 300 seconds
 
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
def parse_github_url(url):
    """Parse GitHub URL to extract owner, repo, branch, and path"""
    path_parts = url.replace('https://github.com/', '').split('/')
   
    owner = path_parts[0]
    repo = path_parts[1]
   
    branch = None  
    path = ''
   
    if len(path_parts) > 2:
        if path_parts[2] == 'tree':
            branch = path_parts[3]
            path = '/'.join(path_parts[4:]) if len(path_parts) > 4 else ''
        elif path_parts[2] == 'blob':
            branch = path_parts[3]
            path = '/'.join(path_parts[4:]) if len(path_parts) > 4 else ''
        else:
            path = '/'.join(path_parts[2:])
   
    return {
        'owner': owner,
        'repo': repo,
        'branch': branch,
        'path': path
    }
 
def generate_model_class(table_name, columns, output_folder):
    """Generate a C# model class based on the table name and columns, dynamically detecting the primary key."""
   
    # Convert table name to PascalCase (e.g., "contact_message" -> "ContactMessage")
    class_name = ''.join(word.capitalize() for word in table_name.split('_'))
   
    # Start the C# class definition
    class_code = f"public class {class_name}\n{{\n"
   
    # Iterate over the columns to find the primary key and generate properties
    primary_key_found = False
    for column in columns:
        column_name = column[0]
        column_type = "string"  # Default to string unless we detect something else
 
        # Map some common column types (you can expand this list)
        if "int" in column[1].__name__:
            column_type = "int"
        elif "date" in column[1].__name__:
            column_type = "DateTime"
        elif "bool" in column[1].__name__:
            column_type = "bool"
       
        # PascalCase for column name (e.g., "user_name" -> "UserName")
        pascal_case_name = ''.join(word.capitalize() for word in column_name.split('_'))
 
        # Check for primary key (typically column name could be 'id', 'uid', etc.)
        if not primary_key_found and (column_name.lower() == "id" or column_name.lower() == "uid"):
            class_code += f"    public {column_type} {pascal_case_name} {{ get; set; }}  // Primary Key\n"
            primary_key_found = True
        else:
            # Add property for other columns
            class_code += f"    public {column_type} {pascal_case_name} {{ get; set; }}\n"
 
    # Close the class definition
    class_code += "}\n"
 
    # Determine the output file path for the model file
    model_file_path = output_folder / "Models" / f"{class_name}.cs"
   
    # Ensure the Models folder exists
    models_folder = output_folder / "Models"
    models_folder.mkdir(parents=True, exist_ok=True)
 
    # Write the class code to the model file
    with open(model_file_path, 'w', encoding='utf-8') as model_file:
        model_file.write(class_code)
   
    print(f"Model class for table {table_name} has been saved to {model_file_path}")
 
def process_access_file(file, output_folder, converted_files, app_dbcontext_path):
    """Convert .mdb or .accdb file to SQL script and update AppDbContext.cs"""
    try:
        file_path = output_folder / file['name']
        download_file(file['download_url'], file_path)
 
        conn_str = f'DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={file_path};'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
 
        # Extract table names from Access database
        table_names = [table.table_name for table in cursor.tables(tableType='TABLE')]
       
        # Convert table names to PascalCase and add them to the AppDbContext.cs file
        add_tables_to_appdbcontext(app_dbcontext_path, table_names)
 
        # SQL Output Path
        sql_output_path = output_folder / (file_path.stem + ".sql")
        with open(sql_output_path, 'w', encoding='utf-8') as sql_file:
            for table in table_names:
                sql_file.write(f"\n-- Table: {table}\n")
                cursor.execute(f"SELECT * FROM {table}")
                column_info = [column[0] for column in cursor.description]
                create_table_sql = f"CREATE TABLE {table} (\n"
                for column in cursor.description:
                    col_name = column[0]
                    col_type = column[1].__name__
                    sql_type = "TEXT" if "str" in col_type else "INTEGER"
                    create_table_sql += f"    {col_name} {sql_type},\n"
                create_table_sql = create_table_sql.rstrip(",\n") + "\n);\n"
                sql_file.write(create_table_sql)
                for row in cursor.fetchall():
                    values = ', '.join([f"'{str(value)}'" if isinstance(value, str) else str(value) for value in row])
                    sql_file.write(f"INSERT INTO {table} VALUES ({values});\n")
       
       
         # Generate model classes for each table
        for table in table_names:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table}")
            columns = cursor.description  # Get column names and types
            generate_model_class(table, columns, output_folder)  
 
 
        cursor.close()
        conn.close()
           
        converted_files[file['path']] = f"Success - Converted to {sql_output_path.name}"
    except Exception as e:
        converted_files[file['path']] = f"Access File Conversion Error: {str(e)}"
        logger.error(f"Error processing Access file {file['name']}: {e}")
 
def add_tables_to_appdbcontext(app_dbcontext_path, table_names):
    """Add DbSet<TEntity> for each table to AppDbContext.cs"""
    # Open AppDbContext.cs for editing or create it if it doesn't exist
    if not app_dbcontext_path.exists():
        app_dbcontext_content = """
using Microsoft.EntityFrameworkCore;
 
public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }
 
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);
    }
}
"""
        with open(app_dbcontext_path, 'w', encoding='utf-8') as f:
            f.write(app_dbcontext_content.strip())
   
    # Now, update the AppDbContext with DbSet<TEntity> for each table
    with open(app_dbcontext_path, 'r+', encoding='utf-8') as f:
        app_dbcontext_content = f.read()
       
        # Add DbSet<TEntity> for each table (converted to PascalCase)
        for table_name in table_names:
            # Convert table name to PascalCase (e.g., "contact_message" -> "ContactMessage")
            entity_name = ''.join(word.capitalize() for word in table_name.split('_'))
            dbset_declaration = f"    public DbSet<{entity_name}> {entity_name}s {{ get; set; }}\n"
           
            # Add the DbSet<TEntity> after the constructor and before the OnModelCreating method
            if 'protected override void OnModelCreating(ModelBuilder modelBuilder)' in app_dbcontext_content:
                app_dbcontext_content = app_dbcontext_content.replace(
                    'protected override void OnModelCreating(ModelBuilder modelBuilder)',
                    f"    // DbSets for entities\n{dbset_declaration}protected override void OnModelCreating(ModelBuilder modelBuilder)"
                )
            else:
                # If no OnModelCreating method, add it at the end of the class
                app_dbcontext_content = app_dbcontext_content.replace(
                    'public class AppDbContext : DbContext',
                    f'public class AppDbContext : DbContext\n{{\n{dbset_declaration}\n'
                )
       
        # Write the updated content back to AppDbContext.cs
        f.seek(0)
        f.write(app_dbcontext_content)
        f.truncate()
   
    print(f"AppDbContext.cs updated with DbSet<TEntity> for tables: {', '.join(table_names)}")
 
def get_default_branch(owner, repo):
    """Fetch the default branch of the repository (either 'main' or 'master')"""
    api_url = f"{GITHUB_API_BASE_URL}/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}"
    }
   
    try:
        response = requests.get(api_url, headers=headers, verify=False, timeout=TIMEOUT)
        if response.status_code == 200:
            repo_info = response.json()
            return repo_info.get("default_branch", "main")  # Default to 'main' if not specified
        else:
            raise Exception(f"GitHub API error: {response.text}")
    except Exception as e:
        raise Exception(f"Failed to fetch repository info: {str(e)}")
   
 
from pathlib import Path

def create_appsettings_file(output_folder: Path):
    """Create the appsettings.json file with default connection string for .NET 8"""
    
    appsettings_content = """
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=localhost;Database=SampleDb;Trusted_Connection=True;"
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft": "Warning",
      "Microsoft.Hosting.Lifetime": "Information"
    }
  },
  "AllowedHosts": "*"
}
"""
    # Ensure the directory exists before writing
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Write the content to the appsettings.json file
    (output_folder / "appsettings.json").write_text(appsettings_content.strip(), encoding='utf-8')
  
 
def download_file(url, output_path):
    """Download a file and save it to the output folder"""
    try:
        response = requests.get(url, verify=False, timeout=TIMEOUT)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            f.write(response.content)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading {url}: {e}")
        raise
 
 
def fetch_github_repo_contents(owner, repo, path="", branch="main"):
    """Fetch repository contents using GitHub API"""
    api_url = f"{GITHUB_API_BASE_URL}/{owner}/{repo}/contents/{path}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}"
    }
    params = {"ref": branch}
 
    try:
        response = requests.get(api_url, headers=headers, params=params, verify=False, timeout=TIMEOUT)
        if response.status_code == 200:
            contents = response.json()
           
            if not isinstance(contents, list):
                contents = [contents]
               
            files = []
            for item in contents:
                if item['type'] == 'file':
                    files.append(item)
                elif item['type'] == 'dir':
                    subdir_files = fetch_github_repo_contents(
                        owner, repo, item['path'], branch
                    )
                    files.extend(subdir_files)
            return files
        else:
            raise Exception(f"GitHub API error: {response.text}")
    except Exception as e:
        raise Exception(f"Failed to fetch repository contents: {str(e)}")
 
def process_file(file, output_folder, converted_files, memory, project_name):
    """Process a single file for conversion"""
    try:
        content = fetch_file_content(file['download_url'])
        file_type = determine_file_type(content, file['name'])
       
        # Pass project_name to convert_file
        converted_content = convert_file(content, file_type, memory, project_name)  # Updated line
        
        output_path = determine_output_path(file, file_type, output_folder)
       
        output_path.parent.mkdir(parents=True, exist_ok=True)
       
        with open(output_path, 'w', encoding='utf-8') as f:
            if file_type == "appsettings":
                json_content = json.loads(converted_content)
                json.dump(json_content, f, indent=2)
            else:
                f.write(converted_content)
               
        converted_files[file['path']] = f"Success - Converted to {file_type}"
       
    except Exception as e:
        converted_files[file['path']] = f"Error: {str(e)}"

 
def determine_file_type(content, filename):
    """Determine the type of file based on content and filename"""
    content_lower = content.lower()
    filename_lower = filename.lower()
   
    # Check for Controller files
    if re.search(r'Request\.Form|Request\.QueryString|Response\.Write', content):
        return "controller"
   
    # Check for Model files
    if re.search(r'Function\s+\w+|Sub\s+\w+|ADODB\.Connection|Recordset\.Open', content):
        return "model"
   
    # Check for View files
    if re.search(r'Response\.Write\s*<|<\s*html|<\s*\!DOCTYPE', content):
        return "view"
   
    # Check for Service files
    if re.search(r'Include\s+File|\.inc', content):
        return "service"
   
    # Check for JavaScript files
    if filename_lower.endswith('.js'):
        return "javascript"
   
    # Check for CSS files
    if filename_lower.endswith('.css'):
        return "css"
   
    # Default to helper files
    return "helper"
 
def determine_output_path(file, file_type, output_folder):
    """Determine the output path for a converted file"""
    file_name = Path(file['name']).stem.capitalize() 
   
    type_paths = {
        "controller": output_folder / "Controllers" / f"{file_name}Controller.cs",
        "model": output_folder / "Models" / f"{file_name}.cs",
        "view": output_folder / "Views" / f"{file_name}.cshtml",
        "service": output_folder / "Services" / f"{file_name}Service.cs",
        "javascript": output_folder / "wwwroot/js" / f"{file_name}.js",
        "css": output_folder / "wwwroot/css" / f"{file_name}.css",
        "helper": output_folder / "Helpers" / f"{file_name}.cs",
    }
   
    return type_paths.get(file_type, output_folder / f"{file_name}.txt")
 
def process_image_file(file, output_folder, converted_files):
    """Process and save image files"""
    try:
        response = requests.get(file['download_url'], verify=False, timeout=TIMEOUT)
        if response.status_code == 200:
            output_path = output_folder / file['name']
            output_path.parent.mkdir(parents=True, exist_ok=True)
           
            with open(output_path, 'wb') as f:
                f.write(response.content)
           
            converted_files[file['path']] = "Success (Image)"
        else:
            raise Exception(f"Failed to download image: {response.status_code}")
    except Exception as e:
        raise Exception(f"Image processing error: {str(e)}")
 
def create_solution_files(output_folder, project_name):
    """Create solution and project files"""
    csproj_content = """
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
 
  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.Mvc.Razor.RuntimeCompilation" Version="7.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="7.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="7.0.0" />
  </ItemGroup>
</Project>
"""
    (output_folder / f"{project_name}.csproj").write_text(csproj_content)
 
    sln_content = f"""
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.0.31903.59
MinimumVisualStudioVersion = 10.0.40219.1
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}", "{project_name}.csproj", "{{8BFEA4E2-7E3D-4D3F-8A44-B5E3595A9D80}}"
EndProject
Global
    GlobalSection(SolutionConfigurationPlatforms) = preSolution
        Debug|Any CPU = Debug|Any CPU
        Release|Any CPU = Release|Any CPU
    EndGlobalSection
EndGlobal
"""
    (output_folder / f"{project_name}.sln").write_text(sln_content)
 
def create_program_cs_file(output_folder, project_name):
    """Create Program.cs file with Swagger integration, middleware configuration, and AppDbContext injection"""

    program_cs_content = f"""
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.EntityFrameworkCore;
using {project_name}.Data; // Assuming AppDbContext is in the Data namespace

namespace {project_name}
{{
    public class Program
    {{
        public static void Main(string[] args)
        {{
            CreateHostBuilder(args).Build().Run();
        }}

        public static IHostBuilder CreateHostBuilder(string[] args) =>
            Host.CreateDefaultBuilder(args)
                .ConfigureWebHostDefaults(webBuilder =>
                {{
                    webBuilder.ConfigureServices(services =>
                    {{
                        // Add services to the container.
                        services.AddControllersWithViews();
                        services.AddSwaggerGen(); // Add Swagger generation
                        
                        // Register AppDbContext with dependency injection
                        services.AddDbContext<AppDbContext>(options =>
                            options.UseSqlServer(Configuration.GetConnectionString("DefaultConnection"))); // Adjust connection string as needed
                    }})
                    .Configure(app =>
                    {{
                        // Configure the HTTP request pipeline.
                        if (app.Environment.IsDevelopment())
                        {{
                            app.UseDeveloperExceptionPage();
                        }}

                        app.UseRouting();

                        app.UseSwagger(); // Enable Swagger UI
                        app.UseSwaggerUI(c =>
                        {{
                            c.SwaggerEndpoint("/swagger/v1/swagger.json", "SampleDbCrud40 API V1");
                            c.RoutePrefix = ""; // Serve Swagger UI at the root
                        }});

                        app.UseEndpoints(endpoints =>
                        {{
                            endpoints.MapControllerRoute(
                                name: "default",
                                pattern: "{{controller=Home}}/{{action=Index}}/{{id?}}");
                        }});
                    }});
                }});
    }}
}}
"""
    (output_folder / "Program.cs").write_text(program_cs_content)

 
# Initialize LangChain memory
# memory = ConversationBufferMemory()
from langchain.memory import ConversationBufferMemory
 
# memory = ConversationBufferMemory(return_messages=True)  # Add parameters if required
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)


    
def convert_file(content, file_type, memory, project_name):
    
    type_prompts = {
        "controller": "Generate the ASP.NET Core Web API controller code only. Do not include any models, DbContext, or configuration details. Just the controller implementation for handling the data. Do not include any language name or markdown code blocks in the output. Use the namespace {namespace}.",
        "model": "Convert the following code to a C# model class, ensuring it uses appropriate data types, properties with validation annotations (if necessary), and follows C# conventions for property and class design: Do not include any language name or markdown code blocks in the output. Use the namespace {namespace}.",
        "view": "Convert the following code to a Razor view, ensuring it’s optimized for clean HTML structure with proper CSS and JavaScript embedded. Make sure it follows MVC conventions for embedding C# code and rendering dynamic data: Do not include any language name or markdown code blocks in the output. Use the namespace {namespace}.",
        "service": "Convert the following code to a C# service class that includes dependency injection, proper business logic separation, and clear method definitions that adhere to SOLID principles: Do not include any language name or markdown code blocks in the output. Use the namespace {namespace}.",
        "javascript": "Optimize and refactor the following JavaScript code for performance, readability, and modern best practices. Ensure it follows ES6+ standards, with clear function and variable declarations, error handling, and optimized logic:",
        "css": "Optimize and refactor the following CSS code for better maintainability and readability. Ensure the use of best practices like variable declarations, proper selector usage, and appropriate layout techniques (e.g., Flexbox, Grid) to ensure responsiveness:",
        "helper": "Convert the following code to a C# utility/helper class, ensuring it provides useful methods with a focus on reusability, clarity, and separation of concerns. The helper class should contain static or instance methods designed for easy integration into other parts of the system: Do not include any language name or markdown code blocks in the output. Use the namespace {namespace}.",
        "html": "Convert the following code to a clean, semantic HTML5 document, ensuring proper tags and structure for accessibility, SEO, and cross-browser compatibility. Focus on ensuring that the HTML is well-formed and that it adheres to current web standards:",
        "python": "Convert the following Python script to an optimized and efficient C# program, ensuring proper memory management, proper error handling, and utilizing C# features like async/await where applicable. The C# code should maintain the same logic while adhering to C# best practices: Do not include any language name or markdown code blocks in the output. Use the namespace {namespace}.",
        "sql": "Convert the following SQL query to a more optimized version, considering indexing, query execution efficiency, and proper use of joins, filters, and database functions. Ensure that the query performs well on large datasets and follows best practices for database optimization:",
        "typescript": "Convert the following JavaScript code to TypeScript, ensuring that types are properly declared, interfaces and types are used where applicable, and the code takes full advantage of TypeScript’s features such as type safety, modules, and advanced ES6+ syntax:"
    }

    # Replace the {namespace} with the project_name
    prompt = type_prompts.get(file_type, "Convert code:").replace("{namespace}", project_name) + f"\n\n{content}"
    
    # Load previous context from memory
    chat_history = memory.load_memory_variables({}).get("chat_history", [])
    messages = [{"role": "system", "content": "You are a code migration specialist."}]
   
    # Add chat history to messages
    for message in chat_history:
        messages.append({"role": "user" if message.type == "human" else "assistant", "content": message.content})
   
    # Add the current prompt
    messages.append({"role": "user", "content": prompt})
 
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_API_KEY
    }
 
    payload = {
        "model": MODEL,
        "messages": messages
    }
 
    try:
        response = requests.post(AZURE_OPENAI_ENDPOINT, json=payload, headers=headers, verify=False, timeout=TIMEOUT)
        if response.status_code == 200:
            response_data = response.json()
            generated_code = response_data["choices"][0]["message"]["content"].strip()
 
            # Check if the code contains markdown-style code blocks and remove them
            if "```" in generated_code:
                code_block_start = generated_code.find("```") + 3
                code_block_end = generated_code.rfind("```")
                generated_code = generated_code[code_block_start:code_block_end].strip()
 
            # Save context to memory
            memory.save_context({"input": prompt}, {"output": generated_code})
 
            return generated_code
        else:
            raise Exception(f"Conversion API error: {response.text}")
    except Exception as e:
        raise Exception(f"Conversion failed: {str(e)}")
 
 
def create_launch_settings(project_name, output_folder):
    """Generate launchSettings.json in the Properties folder of the project."""
   
    # Define the structure of the launchSettings.json file
    launch_settings = {
        "iisSettings": {
            "windowsAuthentication": False,
            "anonymousAuthentication": True,
            "iisExpress": {
                "environmentVariables": {
                    "ASPNETCORE_ENVIRONMENT": "Development"
                }
            }
        },
        "profiles": {
            "IISExpress": {
                "commandName": "IISExpress",
                "environmentVariables": {
                    "ASPNETCORE_ENVIRONMENT": "Development"
                }
            },
            project_name: {
                "commandName": "Project",
                "environmentVariables": {
                    "ASPNETCORE_ENVIRONMENT": "Development"
                },
                "applicationUrl": "http://localhost:5000",
                "dotnetRunMessages": True
            }
        }
    }
 
    # Make sure the Properties folder exists
    properties_folder = output_folder / "Properties"
    properties_folder.mkdir(parents=True, exist_ok=True)
 
    # Define the path for the launchSettings.json file
    launch_settings_path = properties_folder / "launchSettings.json"
 
    # Write the launchSettings.json content to the file
    with open(launch_settings_path, "w") as json_file:
        json.dump(launch_settings, json_file, indent=4)
 
    print(f"launchSettings.json has been created at {launch_settings_path}")
 
def fetch_file_content(file_url):
    try:
        response = requests.get(file_url, verify=False, timeout=TIMEOUT)
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Failed to fetch file: {response.status_code}")
    except Exception as e:
        raise Exception(f"File fetch error: {str(e)}")
   

 
@app.route('/convert', methods=['POST', 'OPTIONS'])
def convert_repo():
    if request.method == 'OPTIONS':
        return jsonify({"status": "OK"}), 200
 
    data = request.get_json()
    repo_url = data.get("repo_url")
 
    if not repo_url:
        return jsonify({"error": "Missing 'repo_url' in request."}), 400
 
    try:
        github_info = parse_github_url(repo_url)
 
        if not github_info['branch']:
            github_info['branch'] = get_default_branch(github_info['owner'], github_info['repo'])
 
        project_name = github_info['path'].split('/')[-1] if github_info['path'] else github_info['repo']
        output_folder = Path(OUTPUT_DIR) / f"ASP.NETCore_{project_name}"
        namespace = project_name.replace(" ", "_").replace("-", "_")
       # Ensure the 'Data' folder exists
        (output_folder / "Data").mkdir(parents=True, exist_ok=True)

        # Set up the app_dbcontext_path
        app_dbcontext_path = output_folder / "Data" / "AppDbContext.cs"
       
        # Create necessary directories
        folders = [
            "Controllers", "Models", "Views", "Data", "Services",
            "wwwroot/js", "wwwroot/css", "wwwroot/images",
            "Properties"
        ]
 
        for folder in folders:
            (output_folder / folder).mkdir(parents=True, exist_ok=True)
 
        # Process repository contents
        repo_contents = fetch_github_repo_contents(
            github_info['owner'],
            github_info['repo'],
            github_info['path'],
            github_info['branch']
        )
 
        converted_files = {}
       
        # Initialize memory for this request
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
 
        # Process files
        with ThreadPoolExecutor() as executor:
            futures = []
            for file in repo_contents:
                file_ext = Path(file['name']).suffix.lower()
                if file_ext in ['.asp', '.aspx', '.html', '.css', '.js', '.inc',
                              '.xml', '.vbs', '.asa', '.config', '.cshtml']:
                    futures.append(
                        executor.submit(
                            process_file,
                            file,
                            output_folder,
                            converted_files,
                            memory,
                            project_name
                        )
                    )
                elif file_ext in ['.mdb', '.accdb']:
                    futures.append(executor.submit(process_access_file, file, output_folder, converted_files, app_dbcontext_path))    
  
            for future in futures:
                future.result()
 
        create_appsettings_file(output_folder)
        create_program_cs_file(output_folder, project_name)
        create_solution_files(output_folder, project_name)
        create_launch_settings(project_name, output_folder)
       
        # Return complete response
        return jsonify({
            "status": "success",
            "project_name": project_name,
            "converted_files": converted_files,
            "output_dir": str(output_folder)
        })
 
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
    
@app.route('/download/<project_name>', methods=['GET'])
def download_project(project_name):
    try:
        safe_project_name = os.path.basename(project_name)
        output_folder = Path(OUTPUT_DIR) / f"ASP.NETCore_{safe_project_name}"
        
        # Debugging the constructed folder path
        logger.debug(f"Checking project folder path: {output_folder}")
        
        if not output_folder.exists():
            logger.error(f"Project folder not found: {output_folder}")
            return jsonify({"status": "error", "error": "Project files not found"}), 404
        
        zip_path = output_folder.parent / f"{safe_project_name}.zip"
        
        if zip_path.exists():
            zip_path.unlink()

        logger.debug(f"Creating zip archive: {zip_path}")
        shutil.make_archive(str(zip_path.with_suffix('')), 'zip', output_folder)

        response = send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{safe_project_name}.zip"
        )
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
