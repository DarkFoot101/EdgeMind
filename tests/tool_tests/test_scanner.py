from app.tools.code_scanner import scan_project
from app.resources.system_monitor import get_system_resources

result = scan_project(".")

system_resources = get_system_resources()

combined_data = {
    "project_analysis" : result,
    "system_info" : system_resources
}

print(combined_data)