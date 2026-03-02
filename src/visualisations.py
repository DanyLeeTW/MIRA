import json
import os
from queue import Queue

import markdown
from termcolor import colored


class EvaluationOutputCollector:
    """
    A class to collect and display output from a simulation of patient and medical doctor interaction and actions.
    """

    def __init__(self, dataset_name, hadm_id):
        """
        Initializes the OutputCollector with a specified filename.

        Parameters:
        - dataset_name (str): The name of the dataset.
        - hadm_id (int): The hospital admission ID.
        """
        directory = os.path.join("formatted_outputs_rerun", dataset_name)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Generate a unique filename if the specified one already exists
        base_filename = f"{dataset_name}_{hadm_id}_conversation"
        extension = ".html"
        counter = 1
        file_path = os.path.join(directory, f"{base_filename}_{counter}{extension}")

        while os.path.exists(file_path):
            counter += 1
            file_path = os.path.join(directory, f"{base_filename}_{counter}{extension}")

        self.filename = file_path
        self.items = []  # Collect messages and actions
        self.contents = []
        self._initialize_html()

    def _initialize_html(self):
        """
        Initializes the HTML file with necessary headers and styles.
        """
        html_header = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>LLM Agent Hospital</title>
            <!-- Include Tailwind CSS via CDN -->
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                /* Custom styles if needed */
                body {
                    background-color: #f9fafb;
                }
            </style>
        </head>
        <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-4xl font-bold mb-8 text-center text-indigo-600">AI Hospital</h1>
            <div id="conversation"></div>
            <div id="restart-button-container" class="text-center mt-4"></div>
        """
        self.contents.append(html_header)

    def display_action(self, action_text: str, action_type: str):
        """
        Collects an action to be displayed later with JavaScript.

        Parameters:
        - action_text (str): The text to display, which can include Markdown syntax.
        - action_type (str): The type of action, used to determine styling.
        """
        # Convert Markdown to HTML
        prepend_messages = {
            "get_blood_value_results": "**Requesting patient lab values ... 🩸🩸🩸**\n\n",
            "get_urine_value_results": "**Requesting patient urine values ... 💧💧💧**\n\n",
            "get_medication_results": "**Requesting and uploading patient medication ... 💊💊💊**\n\n",
            "get_physical_exam_results": "**Performing physical examination. .. 🩺🩺🩺**\n\n",
            "get_microbiology_results": "**Requesting microbiology tests ... 🦠🧫🧬**\n\n",
            "get_radiology_results": "**Requesting radiology examination data ... 🩻🩻🩻**\n\n",
            "get_procedure_search_results": "**Searching for possible procedure options ... 🔍🔍🔍**\n\n",
            "get_procedure_request_results": "**Requesting procedure information ... 💉🏥🩹**\n\n",
            "generate_routine": "**Generating plan ... 🍓🍓🍓**\n\n",
            "finish": "**Admitted to hospital ... 👩🏼‍⚕️👨🏿‍⚕️👩🏽‍⚕️**\n\n",
        }
        prepend_msg = prepend_messages.get(action_type, "**Processing request...**\n\n")
        full_action_text = prepend_msg + action_text
        action_html = markdown.markdown(full_action_text)

        self.items.append(
            {
                "type": "action",
                "action_type": action_type,
                "action_text": action_html,  # Store the HTML content
            }
        )

        # Print simplified version to console
        print(f"Action ({action_type}): {action_text}")

    def display_message(self, name: str, message: str):
        """
        Collects a message to be displayed later with JavaScript.

        Parameters:
        - name (str): The name to display (e.g., "Medical Doctor").
        - message (str): The message content.
        """
        # Convert Markdown to HTML
        message_html = markdown.markdown(message)

        self.items.append(
            {
                "type": "message",
                "name": name,
                "message": message_html,  # Store the HTML content
            }
        )

        # Print simplified version to console
        if name == "Medical Doctor":
            print(colored(f"{name}: {message}", "green"))
        else:
            print(colored(f"{name}: {message}", "blue"))

    def save(self):
        """
        Saves the collected HTML content to the specified file, allowing either immediate display of all messages
        or a streamed typing effect triggered by a button.
        """
        items_json = json.dumps(self.items, ensure_ascii=False).replace("</", "<\\/")
        json_script = f"""
        <script type="application/json" id="items-data">
        {items_json}
        </script>
        """

        script = """
        <script>
        let streamingEnabled = false; 

        const items = JSON.parse(document.getElementById('items-data').textContent);

        const conversationDiv = document.getElementById('conversation');
        const restartButtonContainer = document.getElementById('restart-button-container');
        const streamButton = document.getElementById('stream-button');
        let currentIndex = 0;

        streamButton.addEventListener('click', () => {
            streamingEnabled = true;
            conversationDiv.innerHTML = '';
            restartButtonContainer.innerHTML = '';
            currentIndex = 0;
            showNextItem();
        });

        function typeText(element, htmlContent, callback) {
            let tempDiv = document.createElement('div');
            tempDiv.innerHTML = htmlContent;
            const nodes = Array.from(tempDiv.childNodes);

            function processNode(node, parent, callback) {
                if (node.nodeType === Node.TEXT_NODE) {
                    typeTextNode(node, parent, callback);
                } else if (node.nodeType === Node.ELEMENT_NODE) {
                    let newNode = document.createElement(node.nodeName);
                    for (let attr of node.attributes) {
                        newNode.setAttribute(attr.name, attr.value);
                    }
                    parent.appendChild(newNode);
                    let childNodes = Array.from(node.childNodes);
                    processNodes(childNodes, newNode, callback);
                }
            }

            function processNodes(nodes, parent, callback) {
                if (nodes.length === 0) {
                    if (callback) callback();
                    return;
                }
                let node = nodes.shift();
                processNode(node, parent, function() {
                    processNodes(nodes, parent, callback);
                });
            }

            function typeTextNode(textNode, parent, callback) {
                let text = textNode.textContent;
                let index = 0;
                let newNode = document.createTextNode('');
                parent.appendChild(newNode);

                function typeChar() {
                    if (index < text.length) {
                        newNode.textContent += text.charAt(index);
                        index++;
                        setTimeout(typeChar, 3);
                    } else {
                        if (callback) callback();
                    }
                }
                typeChar();
            }

            processNodes(nodes, element, callback);
        }

        function showNextItem() {
            if (!streamingEnabled) return; 
            if (currentIndex >= items.length) {
                showRestartButton();
                return;
            }

            const item = items[currentIndex];
            currentIndex++;

            if (item.type === 'message') {
                const messageDiv = document.createElement('div');
                messageDiv.classList.add('flex', 'items-start', 'mb-6');

                const nameColor = item.name === 'Medical Doctor' ? 'text-indigo-600' : 'text-green-600';
                const bgColor = item.name === 'Medical Doctor' ? 'bg-indigo-50' : 'bg-green-50';

                messageDiv.innerHTML = `
                    <div class="flex-shrink-0">
                        <div class="h-12 w-12 rounded-full flex items-center justify-center ${bgColor}">
                            <span class="text-2xl ${nameColor} font-bold">${item.name.charAt(0)}</span>
                        </div>
                    </div>
                    <div class="ml-4">
                        <div class="text-lg ${nameColor} font-semibold">${item.name}</div>
                        <div class="mt-1 text-gray-700" id="message-content-${currentIndex}">
                        </div>
                    </div>
                `;
                conversationDiv.appendChild(messageDiv);

                const messageContentDiv = document.getElementById('message-content-' + currentIndex);
                const htmlContent = item.message;
                typeText(messageContentDiv, htmlContent, () => {
                    setTimeout(showNextItem, 100);
                });
            } else if (item.type === 'action') {
                const colorMapping = {
                    "get_blood_value_results": "bg-red-100 border-red-500 text-red-800",
                    "get_medication_results": "bg-yellow-100 border-yellow-500 text-yellow-800",
                    "get_physical_exam_results": "bg-gray-100 border-gray-500 text-gray-800",
                    "get_microbiology_results": "bg-green-100 border-green-500 text-green-800",
                    "get_radiology_results": "bg-blue-100 border-blue-500 text-blue-800",
                    "get_urine_value_results": "bg-sky-100 border-sky-500 text-sky-800",
                    "get_procedure_search_results": "bg-purple-100 border-purple-500 text-purple-800",
                    "get_procedure_request_results": "bg-pink-100 border-pink-500 text-pink-800",
                    "generate_routine": "bg-pink-100 border-pink-500 text-pink-800",
                    "finish": "bg-teal-100 border-teal-500 text-teal-800",
                };

                const colorClasses = colorMapping[item.action_type] || "bg-blue-100 border-blue-500 text-blue-800";

                const actionDiv = document.createElement('div');
                actionDiv.classList.add('mb-6');
                actionDiv.innerHTML = `
                    <div class="border-l-4 ${colorClasses} p-6 rounded-lg shadow-md">
                        ${item.action_text}
                    </div>
                `;
                conversationDiv.appendChild(actionDiv);

                setTimeout(showNextItem, 100);
            }
        }

        function showRestartButton() {
            restartButtonContainer.innerHTML = '';
            const button = document.createElement('button');
            button.classList.add('bg-indigo-600', 'text-white', 'px-4', 'py-2', 'rounded', 'hover:bg-indigo-700');
            button.textContent = 'Restart Conversation';
            button.addEventListener('click', () => {
                conversationDiv.innerHTML = '';
                restartButtonContainer.innerHTML = '';
                currentIndex = 0;
                showNextItem();
            });
            restartButtonContainer.appendChild(button);
        }

        // If streaming is not enabled, directly show all items without streaming
        if (!streamingEnabled) {
            for (const item of items) {
                if (item.type === 'message') {
                    const messageDiv = document.createElement('div');
                    messageDiv.classList.add('flex', 'items-start', 'mb-6');

                    const nameColor = item.name === 'Medical Doctor' ? 'text-indigo-600' : 'text-green-600';
                    const bgColor = item.name === 'Medical Doctor' ? 'bg-indigo-50' : 'bg-green-50';

                    messageDiv.innerHTML = `
                        <div class="flex-shrink-0">
                            <div class="h-12 w-12 rounded-full flex items-center justify-center ${bgColor}">
                                <span class="text-2xl ${nameColor} font-bold">${item.name.charAt(0)}</span>
                            </div>
                        </div>
                        <div class="ml-4">
                            <div class="text-lg ${nameColor} font-semibold">${item.name}</div>
                            <div class="mt-1 text-gray-700">
                                ${item.message}
                            </div>
                        </div>
                    `;
                    conversationDiv.appendChild(messageDiv);

                } else if (item.type === 'action') {
                    const colorMapping = {
                        "get_blood_value_results": "bg-red-100 border-red-500 text-red-800",
                        "get_medication_results": "bg-yellow-100 border-yellow-500 text-yellow-800",
                        "get_physical_exam_results": "bg-gray-100 border-gray-500 text-gray-800",
                        "get_microbiology_results": "bg-green-100 border-green-500 text-green-800",
                        "get_radiology_results": "bg-blue-100 border-blue-500 text-blue-800",
                        "get_urine_value_results": "bg-sky-100 border-sky-500 text-sky-800",
                        "get_procedure_search_results": "bg-purple-100 border-purple-500 text-purple-800",
                        "get_procedure_request_results": "bg-pink-100 border-pink-500 text-pink-800",
                        "generate_routine": "bg-pink-100 border-pink-500 text-pink-800",
                        "finish": "bg-teal-100 border-teal-500 text-teal-800",
                    };

                    const colorClasses = colorMapping[item.action_type] || "bg-blue-100 border-blue-500 text-blue-800";

                    const actionDiv = document.createElement('div');
                    actionDiv.classList.add('mb-6');
                    actionDiv.innerHTML = `
                        <div class="border-l-4 ${colorClasses} p-6 rounded-lg shadow-md">
                            ${item.action_text}
                        </div>
                    `;
                    conversationDiv.appendChild(actionDiv);
                }
            }
        }
        </script>
        """

        # Add a 'Stream' button at the top
        stream_button_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.16/dist/tailwind.min.css" rel="stylesheet">
        </head>
        <body class="bg-white text-gray-900">
        <div class="p-4">
            <button id="stream-button" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 mb-4">Enable Streaming</button>
            <div id="conversation"></div>
            <div id="restart-button-container" class="mt-4"></div>
        </div>
        """

        self.contents = [
            stream_button_html,
            json_script,
            script,
            "</div></body></html>",
        ]
        full_html = "\n".join(self.contents)

        with open(self.filename, "w", encoding="utf-8") as f:
            f.write(full_html)
        os.chmod(self.filename, 0o444)

        print(f"Saved conversation to {self.filename}")


class GradioOutputCollector:
    """
    This class is used to collect and display output from a simulation of patient and medical doctor interaction and actions.
    Used only in demonstration mode via gradio.
    """

    def __init__(self, hadm_id=None, dataset_name=None, message_queue=None):
        self.hadm_id: int = hadm_id
        self.dataset_name: str = dataset_name
        self.messages: list = []
        self.message_queue: Queue = message_queue  # Queue to send messages to Gradio

    def display_message(self, speaker_name, message):
        self.messages.append({"speaker": speaker_name, "message": message})
        if self.message_queue:
            self.message_queue.put({"speaker": speaker_name, "message": message})
