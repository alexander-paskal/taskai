


help_general = """

Welcome to Task! Here's what you can do:

'task show all' --> show all of your lists and item names, with their respective IDs prepended
'task show {id or substring}' --> find the list or item matching your identifier and show it using its respective type's show command
'task show list {id or substring}' --> show the list and all of its item names
'task show item {id}' --> show the associated item and all of its specified information
'task show items {id1},{id2},...,{idx}' --> show the associated items and all of their specified information
'task create item {list id or substring} {name} {**kwargs}' --> Create a new item for the associated list. Can specify kwargs as --optional cli arguments. 
'task create list {name}' --> create a new list by that name
'task delete {id}' --> deletes the list or item associated with that id
'task delete item {id}' --> deletes the item associated with that id
'task delete list {id}' --> deletes the list associated with that id
'task delete completed' --> deletes all items that have been completed
'task remove ...' --> aliases directly to 'task delete ...
'task update {item id} {**kwargs}' --> updates the associated attributes on the item
'task comment {item id} {content}' --> adds a comment to that items comment thread
'task ai {prompt}' --> Feeds a prompt directly to an LLM, which constructs and executes a series of task commands according to its interpretation of the prompt
'task ai headstart {item id}' --> Feeds the item context to an LLM, which responds with a concise description of the next step to perform. The response is added as a comment in the items comment thread
'task nuke' --> deletes all of your task data, letting you have a fresh start
'task add ...' -> aliases directly to 'task create item ...'
'task complete {item id}' --> sets the associated item's .completed attribute to true

Run 'task show examples' to print a comprehensive set of examples, and grep for the ones that you're interested in!

"""


help_menu = {
    "general": help_general,
}