# 6-20

Let's think critically about what i want this API to lookk like. How should be people be
using the CLI?


task create {name} {**kwargs} -> create an item
task add {parent_id} ...  -> create an item as a child
task show all
task show {id}



# 6-19

Really this whole thing should just be a tree abstraction, and I should have a root node class
and just built a tree database with some attrs depending on the type

idk why i'm being a dipshit
But that's gonna be the next iteration

# 6-18

Everything is fucked up anyways lol so might as qweell make some decisions about
the best way to do the database



```python
class DB:

    def get_item(id: int) -> TodoItem:
    def get_comment(id: int) -> Comment:
    def get_config() -> CLIConfig:
    def create_item(name: str, parent: Optional[TodoItem]=None, ...) -> str:
    def create_comment(content: str, parent: TodoItem) -> str:
    def delete_item(name: str) -> bool:
    def delete_comment(name: str) -> bool:
    def update_item(id_: int, kwargs) -> bool:
    def update_comment(id_: int, kwargs) -> bool:
    def update_config(kwargs) -> bool:

    def connect():
        pass
    def commit():
        pass
    def validate():
        pass

``` 

Important factors:
- do i want to serialize/deserialize every record twice? probably not
- so let's make sure that everything is read-only

How do i want to handle parentage? 
i could:
- do it at the client level i.e. make sure to call (add parent)
- do it at the db level i.e. on every create, update, and delete method, validate

Let's do it at the db level - i want the database to be responsible for ensuring data
validation so I don't have to worry about it when I'm writing code downstream


# 6-17

Alright I find myself needing to make some design decisions about hierarchical lists.

I could:
    - differentiate between child items and child lists, and have items only be leaf nodes
        pros:
        cons:
    - treat everything as a single "item" and simply due away with the concept of lists as a
      separate data point
    - still distinguish between the two but treat them all as child ids - useful for sorting

Looking at it, i see no good reason to distinguish between items and lists - it complicates the
code without adding any additional functionality. There is nothing that a list does that an item
can't do apart from be a container, and there's no reason why an item can't also be a container.

So let's just go ahead and implement that change. 


# 6-14

Damn it's been a productive couple of weeks. App is deployed on PyPi and I'm starting to think
a bit more about phase 2, how to rewrite it for ultimate success. What I'm thinking is that
things like help, argument patterns, and service logics should be bundled into one unit - 

the core infrastructure should basically load all of the services in the config, and pull their
argument pattern matching, help menus, etc. That way, the core of the app just works as a dispatcher

Things I need to have clearly in mind before I start rearchitecting:
- How i'm going to handle modularity and reuse for major components
- How i'm going to handle multiple threads and processes
    - a note on this - i'm leaning towards having a core metadata file that just keeps track
    of all processes, that we just read/write to (with some sort of locking mechanism). That
    will maintain process ids and any other shared state

But before all that good stuff, let's take what we have and polish the hell out of it


Also, as I'm doing this, it's becoming clear to me that I need to have records be a bit
more object oriented, as the number of different interactions that have to take place is 
getting more and more annoying to keep track of and the best place for everything to be
put would be as methods on the objects, i.e. "item.updateList()", etc.


# 6-3

Alright so how are comments gonna look here:

    ```
    Name:
    Due By:
    Description:
    Depends On:
    Comments

    ```


Let's think about what this cli refactor is gonna look like:


arg
    arg
        ...
            endpoint, *args, **kwargs



# 5-28

A couple things that I need to deal with:
- recursive deletes (so deleting hierarchical items)
- recursive completes
- better recurrence strategies
- how to deal with linking tasks that are recurrence of the same task
- database server

# 5-27

Let's think about this cli:

what do i want to be able to do?




- task add item|list|comment
- task show item|list|comment
- task complete {id}
- task delete {id}
- task {id} depends_on {id}
- task dependency_chain


- task {id} delete|done|show|edit


Let's start with some views

need to have recursive delete for lists

# 5-26

What can I build right now?

I want to have a basic CLI version of what I want. So we can use a pickle database,
define our models, and add the basic functionality to the core business logic. 


How can we design this?

- I could have a core app session that is built through some composition
- for different concurrent users, we could spin up different processes?
    - why don't I worry about scaling when it comes time to scale, let's just build osmething cool and useful right now

- So we have the app session object, and we can spin it up:
    - on startup
        - connect to a database
    - call methods to perform the actions we care about
        - commit changes as we want
        OR
        - have a plugin architecture where we can add views/operations that take in the session object
    - on exit

CLI version
    - do I want it to run in the background and communicate via pipes?
        - feels like that falls under premature optimization, maybe just try running everything at once to start
        - though that could be fun? maybe next start
    - maybe not a pickle database, can do a local folder json database



so:
    Session:
        def __init__(
            user: User,
            database: Database
        )

        def on_exit():
            ...

    cli/
        views/       --> views of the core data
        services/    --> core business operations we can perform
        cli.py





        





# 5-11

Alright let's think about backend

What is the point of this app? What do I want to be able to support?
- 



# 4-29

Alright let's think about frontend:

- Login Page:
     - Page 1: login
        - if logged in, show main
    
     - Main Page
        - SideBar
        - MainPanel
            - MainPanelOptions

            - TodoPanel
            - EditPanel
            - CanvasPanel


What I want to do:
- build the threads part
- build the login and user context part
- build the database backend interactions
- build the canvas part


How do I want to handle components?

Brainstorm:
- I could construct a component tree
    - each component could have a render call? Or just be called in its constructor, so when you instantiate
    it, it shows up
- I want to have statically defined models so that I don't have to reconstitute things (since that's a pain)



Alright yeah, components can also have a commit-esque method (although maybe that's case by case) where I
commit their data

In that sense, I don't even really need to predefine my HTML - I can just generate it on the fly and have my core
div structure be defined


So what would that look like?

<LoginForm>
<Main>
  <div> flex-col
  <TopPanel>
    
  <div> flex-row
      <SideBar>
      <TodoPanel>
      <EditPanel>
      <CanvasPanel>        

  <footer>



I can just have so many classes:
components/
  loginForm.js
  sidebar.js
  todopanel.js
  editpanel.js
  canvaspanel.js

lib/
  component.js
  database.js
  utils.js


Alright let's start to sketch these out:

We have our base:


    class Component extends HTMLComponent{

        db attribute
        state attribute

        constructor (
            super()
            const shadow = this.attachShadow({mode: 'open'})
            customElements.define(this.constructor.name, this.constructor)
        )
    }


    class LoginForm extends Component {
        constructor(
            super()




        )
    }











# 4-27


Alright sick progress, I'm in the process of populating the database. Now I need to:
- write the startup() method that pulls lists from the database and populates them in the sidebar
    ---> I'll put the populateDb method in there for now

- write the callback so that when I click on a list, it pulls its id from the database 
- write the rendering functions so that the todo-list-panel renders the todos for the selected list


# 4-26

What do I want to add?

Pages:
- login page
- Main Page


# Features that I want to add

- Pop Up Card Editing
- Comments
- Text CLI
- Dockerize
-  