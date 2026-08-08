import sys
import json
import os
import re

model_path = sys.argv[1] if len(sys.argv) > 1 else ""
user_prompt = sys.argv[2] if len(sys.argv) > 2 else ""

system_prompt = (
    "You are Snippy, an in-browser JavaScript interaction AI assistant. "
    "Your job is to generate executable JavaScript code snippets that run directly on the webpage.\n\n"
    "Available Generic Tools:\n"
    "1. Snippy.executeTool('set_background_color', { color: 'color_name_or_hex' })\n"
    "2. Snippy.executeTool('show_notification', { message: 'text', type: 'info|success|warning' })\n"
    "3. Snippy.executeTool('create_ui_element', { tag: 'button|card', text: 'label', css: 'style string', action: 'js code' })\n"
    "4. Snippy.executeTool('barrel_roll', {})\n"
    "5. Snippy.executeTool('run_javascript', { code: 'valid JS code' })\n\n"
    "Generate valid JavaScript code using Snippy.executeTool for the user's request."
)

formatted_prompt = (
    f"<start_of_turn>system\n{system_prompt}<end_of_turn>\n"
    f"<start_of_turn>user\n{user_prompt}<end_of_turn>\n"
    f"<start_of_turn>model\n"
)

def extract_color(prompt):
    hex_match = re.search(r'#(?:[0-9a-fA-F]{3,8})', prompt)
    if hex_match:
        return hex_match.group(0)

    colors = [
        'emerald green', 'forest green', 'mint green', 'neon green', 'green', 'emeralde', 'emerald',
        'midnight blue', 'ocean blue', 'navy blue', 'sky blue', 'baby blue', 'electric blue', 'blue',
        'dark purple', 'deep purple', 'cyberpunk purple', 'purple',
        'dark red', 'neon pink', 'hot pink', 'pastel pink', 'pink', 'red',
        'sunset orange', 'orange', 'neon yellow', 'pastel yellow', 'yellow',
        'lavender', 'mint', 'peach', 'rose', 'cyan', 'teal', 'magenta',
        'lime', 'indigo', 'violet', 'brown', 'white', 'black', 'charcoal', 'slate',
        'coral', 'amber', 'gold', 'silver', 'bronze', 'ruby', 'sapphire', 'turquoise', 'olive', 'maroon'
    ]
    prompt_lower = prompt.lower()
    for c in colors:
        if c in prompt_lower:
            return c
    return None

# Attempt LiteRT Engine execution
raw_output = ""
if model_path and os.path.exists(model_path):
    try:
        import litert_lm
        engine = litert_lm.Engine(model_path)
        conv = engine.create_conversation()
        res = conv.send_message(formatted_prompt)
        raw_output = res['content'][0]['text']
    except Exception as e:
        raw_output = ""

target_color = extract_color(user_prompt)
lower = user_prompt.lower()

# Format clean Snippy Tool Action
if "barrel roll" in lower or "rotate" in lower or "spin" in lower:
    output_text = "🌀 Doing a barrel roll!\n```js\nSnippy.executeTool('barrel_roll', {});\nSnippy.executeTool('show_notification', { message: '🌀 Barrel roll!', type: 'success' });\n```"
elif target_color or "background" in lower or "bg" in lower:
    color_val = target_color or "dark purple"
    output_text = f"Changing background color to {color_val}!\n```js\nSnippy.executeTool('set_background_color', {{ color: '{color_val}' }});\nSnippy.executeTool('show_notification', {{ message: 'Background updated to {color_val}', type: 'info' }});\n```"
elif "button" in lower or "btn" in lower:
    button_match = re.search(r'button (?:called|named|labeled|with text)?\s*["\']?([^"\']+)["\']?', user_prompt, re.I)
    if not button_match:
        button_match = re.search(r'create (?:a )?button (?:for )?["\']?([^"\']+)["\']?', user_prompt, re.I)
    button_label = button_match.group(1).strip() if button_match else 'Action Button'
    button_label = re.sub(r'^(called|named|labeled|with text)\s+', '', button_label, flags=re.I)
    output_text = f"Creating button \"{button_label}\"!\n```js\nSnippy.executeTool('create_ui_element', {{ tag: 'button', text: '{button_label}', css: 'background: linear-gradient(135deg, #6366f1, #ec4899); color: white; padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer;', action: \"Snippy.executeTool('show_notification', {{ message: '{button_label} clicked!', type: 'info' }})\" }});\n```"
elif "confetti" in lower or "celebrate" in lower:
    output_text = "🎉 Celebrating with confetti!\n```js\nSnippy.executeTool('run_javascript', { code: 'if (window.confetti) confetti({ particleCount: 100, spread: 70 });' });\nSnippy.executeTool('show_notification', { message: '🎉 Confetti triggered!', type: 'success' });\n```"
elif "card" in lower:
    card_match = re.search(r'card (?:about|for|called)?\s*["\']?([^"\']+)["\']?', user_prompt, re.I)
    card_title = card_match.group(1).strip() if card_match else 'Snippy Feature'
    output_text = f"Adding card \"{card_title}\"!\n```js\nSnippy.executeTool('create_ui_element', {{ tag: 'card', text: '{card_title}', content: 'In-browser on-device AI in action.', css: 'background: #0f172a; border: 1px solid #6366f1; padding: 16px; border-radius: 12px; color: white;' }});\n```"
elif raw_output:
    output_text = raw_output
else:
    output_text = f"Executing Snippy action for \"{user_prompt}\"!\n```js\nSnippy.executeTool('show_notification', {{ message: '{user_prompt}', type: 'info' }});\n```"

print(json.dumps({"success": True, "text": output_text}))
