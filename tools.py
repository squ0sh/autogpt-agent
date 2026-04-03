def run_tool(action):
    act = action.get("action")
    inp = action.get("input")

    if act == "write":
        return f"Generated content: {inp}"

    elif act == "analyze":
        return f"Analysis: {inp}"

    elif act == "search":
        return f"Search results for: {inp}"

    return "Unknown action"
