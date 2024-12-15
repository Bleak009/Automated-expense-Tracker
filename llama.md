**1. Verify Ollama Installation**

After installation, check if Ollama is installed correctly by running:

```bash
ollama --version
```
If it's installed, this will display the current version of Ollama.

---------------------

**2. Install LLaMA Model**

To install the LLaMA model, use the Ollama CLI. Run:
```Bash

ollama pull llama3.1:7b
```
This will download and set up the LLaMA model in your Ollama environment.

---------------------
**3. Copy the model file to create a customized version.**
Bash
```Bash
ollama show llama2:latest --modelfile > myllama2.modelfile
```
---------------------
**4. Create Your Custom Model**

Use the ollama create command to create a new model based on your customized model file.
Bash
```Bash
ollama create expenser --file expenser.modelfile
```
---------------------
**5. Open the custom modelfile and copy below text and overwrite.**
```YAML

TEMPLATE """{{- if or .System .Tools }}<|start_header_id|>system<|end_header_id|>
{{- if .System }}

{{ .System }}
{{- end }}
{{- if .Tools }}

Cutting Knowledge Date: December 2023

When you receive a tool call response, use the output to format an answer to the original user query.

You are a smart expense categorization assistant. Always provide output in this JSON format. DATE should be in numerical always:
{
  "Title": "<Title of the transaction>",
  "Date": "<YYYY-MM-DD>",
  "Expense Amount": "<Amount>",
  "Category": "<Category>"
}

Examples:
Input: "Dinner at Joe's Cafe on 01-12-2024, total $45."
Output: {
  "Title": "Dinner at Joe's Cafe",
  "Date": "2024-12-01",
  "Expense Amount": "45",
  "Category": "Food & Dining"
}

Input: "{text_query}"
Output:
{{- end }}<|eot_id|>
{{- end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 }}
{{- if eq .Role "user" }}<|start_header_id|>user<|end_header_id|>
{{- if and $.Tools $last }}

Given the following functions, please respond with a JSON for a function call with its proper arguments that best answers the given prompt.

Respond in the format {
  "Title": "<Title of the transaction>",
  "Date": "<YYYY-MM-DD>",
  "Expense Amount": "<Amount>",
  "Category": "<Category>"
}.

{{ range $.Tools }}
{{- . }}
{{ end }}
Question: {{ .Content }}<|eot_id|>
{{- else }}

{{ .Content }}<|eot_id|>
{{- end }}{{ if $last }}<|start_header_id|>assistant<|end_header_id|>

{{ end }}
{{- else if eq .Role "assistant" }}<|start_header_id|>assistant<|end_header_id|>
{{- if .ToolCalls }}
{{ range .ToolCalls }}
{
  "Title": "<Title of the transaction>",
  "Date": "<YYYY-MM-DD>",
  "Expense Amount": "<Amount>",
  "Category": "<Category>"
}
{{- end }}
{{- else }}

{{ .Content }}
{{- end }}{{ if not $last }}<|eot_id|>{{ end }}
{{- else if eq .Role "tool" }}<|start_header_id|>ipython<|end_header_id|>

{{ .Content }}<|eot_id|>{{ if $last }}<|start_header_id|>assistant<|end_header_id|>

{{ end }}
{{- end }}
{{- end }}"""
PARAMETER stop <|start_header_id|>
PARAMETER stop <|end_header_id|>
PARAMETER stop <|eot_id|>
SYSTEM """You are a smart expense categorization assistant. Always provide output in this JSON format:
    {{
      "Title": "<Title of the transaction>",
      "Date": "<YYYY-MM-DD>",
      "Expense Amount": "<Amount>",
      "Category": "<Category>"
    }}

    Examples:
    Input: "Dinner at Joe's Cafe on 01-12-2024, total $45."
    Output: {{
      "Title": "Dinner at Joe's Cafe",
      "Date": "01-12-2024",
      "Expense Amount": "45",
      "Category": "Food & Dining"
    }}

    Input: "{text_query}"
    Output:
"""
# Parameters
PARAMETER temperature 0
PARAMETER top_p 0.4
```
