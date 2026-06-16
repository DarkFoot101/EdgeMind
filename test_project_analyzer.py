from app.tools.project_analyzer import analyze_project

report = analyze_project(".")

print("\n========================")
print("PROJECT ANALYSIS REPORT")
print("========================\n")

print("Project Info:")
print(report["project_info"])

print("\nResources:")
print(report["resources"])

print("\nSelected Model:")
print(report["selected_model"])

print("\nAI Analysis:\n")
print(report["analysis"])