<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/logo.dark.png" width="300">
  <source media="(prefers-color-scheme: light)" srcset="docs/images/logo.light.png" width="300">
  <img alt="logo" src="https://github.com/n-splv/promptsub-py/raw/main/docs/images/logo.light.png" width="300">
</picture>

# Prompt substitution for humans
Promptsub will help you create parametrized prompts for language models, 
when the set of parameters may change for each sample. It pursues two goals:
1. Make it easy for developers to build template- and parameter-agnostic
workflows. It means that at some point in your app you can combine a prompt
template with some parameters, both of which you know nothing about.
And if the result is not empty - you are good to go. 

2. Create a simple and human-readable syntax for writing parametrized templates,
such that even the non-technical people could do it. 

# Contents
- [Usage](#usage)
  * [Creating a simple prompt](#creating-a-simple-prompt)
  * [Testing an advanced prompt](#testing-an-advanced-prompt)
  * [Application example](#application-example)
- [Syntax guide](#syntax-guide)
  * [Basic syntax](#basic-syntax)
  * [Advanced syntax](#advanced-syntax)
  * [Syntax rules](#syntax-rules)
- [Caveats](#caveats)
- [Possible improvements](#possible-improvements)

# Usage

The neat Syntax for writing templates is a major part of promptsub, and you can read
all about it in [the next section](#syntax-guide). 

But first let's run through the API, so that you could better understand the 
purpose of this project. The installation is casual:

```
% pip install promptsub
```
## Creating a simple prompt
```python
from promptsub import Prompt

template = "Say hello [to {name}]"
prompt = Prompt(template)
```

When we create an instance of Prompt, the input string gets parsed and 
checked for syntax errors - if any are found, we receive an informative 
exception:
```python
invalid_template = "Say hello [to {name}"
Prompt(invalid_template)
```
```
  File "<string>", line 1
    Say hello [to {name}
              ^
promptsub.errors.PromptSyntaxError: Template not closed
```

After creation the prompt object can be easily used with any valid parameters:
```python
parameters_batch = (
    {"name": "John", "age": 26},
    {"name": ""},
    {},
}

for params in parameters_batch:
    message = prompt.substitute(params)
    print(message)

# "Say hello to John"
# "Say hello"
# "Say hello"
```
```
# The following parameters are accepted:
InputParams: TypeAlias = dict[str, str | int | float]
```

## Testing an advanced prompt
Let's write a template for a movie suggestion app. We anticipate that not all 
of our users will have filled in their *favourite titles*; in such cases, it's 
better to ask them about their preferences. Also, a user may ask for 
recommendations within a specific *genre* or without any restrictions. Finally, 
it's not uncommon for a user's *name* to be missing.
```python
template = """
Recommend a [{movie_genre}|movie] to [{user_name}|the user], 
who is a fan of {favourite_title} 
|
Ask [{user_name}|the user] about their favourite [{movie_genre}|film]
"""
prompt = Prompt(template)
```
Okay, having no syntax errors is a good place to start. The next thing we should
do is to "play around" with this template to see how it behaves with different 
sets of parameters. Our prompt has a convinient attribute to show all its
variables: 
```python
prompt.variables

# [
#   (required={'favourite_title'}, optional={'user_name', 'movie_genre'}), 
#   (required=set(), optional={'movie_genre', 'user_name'})
# ]
```
The template has two upper level [options](#multiple-template-options) divided 
by a separator: "Recommend..." and "Ask...". If the first one fails due to the
absence of required variables in parameters, the second one will be used.

Now we can create arbitrary values for the variables and check the results.
Note that **an empty string value is equivalent to a missing key**. 
```python
# A similar method will probably be added to the API

from itertools import product


def test_prompt(prompt: Prompt, test_params: dict):
    value_combinations = product(*test_params.values())
    
    for values in value_combinations:
        params = dict(zip(test_params.keys(), values))
        print(prompt.substitute(params))
```
```python
test_params = {
    "movie_genre": ["romantic comedy", ""],
    "favourite_title": ["Rio Bravo (1959)", ""],
    "user_name": ["Quentin", ""],
}
test_prompt(prompt, test_params)

# Recommend a romantic comedy to Quentin, who is a fan of Rio Bravo (1959)
# Recommend a romantic comedy to the user, who is a fan of Rio Bravo (1959)
# Ask Quentin about their favourite romantic comedy
# Ask the user about their favourite romantic comedy
# Recommend a movie to Quentin, who is a fan of Rio Bravo (1959)
# Recommend a movie to the user, who is a fan of Rio Bravo (1959)
# Ask Quentin about their favourite film
# Ask the user about their favourite film
```

## Application example
Here is a simple app that receives a prompt template and some 
parameters. It then combines them to obtain an input message for a language
model, queries that model and returns its response - all while knowing *nothing*
about the template or the parameters.

There are exactly three things that can go wrong here:
1. The template is empty or incompatible with the promptsub syntax. This would 
trigger a "PromptSyntaxError";
2. The parameters contain keys or values of unsupported types. In such case, a
"ParametersTypeError" is raised;
3. After the substitution we end up with an empty string. It means that at least
one of the required variables has not been provided. There is no exception for 
this situation, because subsequent actions would mostly depend on your specific 
business logic.

In our example, we diligently report all errors to the client.
```python
from functools import partial

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from promptsub import Prompt
from promptsub.errors import ParametersTypeError, PromptSyntaxError
from pydantic import BaseModel


app = FastAPI()
http_400 = partial(HTTPException, status_code=400)


class Request(BaseModel):
    template: str
    params: dict
    
    
def get_response_from_language_model(message: str) -> str:
    ...


@app.exception_handler(PromptSyntaxError)
def syntax_exception_handler(request, exc):
    raise http_400(detail=f"Error in template: {exc}")
    

@app.exception_handler(ParametersTypeError)
def params_exception_handler(request, exc):
    raise http_400(detail=f"Error in params: {exc}")


@app.post("/ask_language_model")
def generate_response(request: Request):

    prompt = Prompt(request.template)
    message = prompt.substitute(request.params)
    
    if message == "":
        raise http_400(detail="Required variable not provided")
    
    response = get_response_from_language_model(message)
    return JSONResponse(content={"response": response})
```
In a real project your template and params may originate from different places,
e.g. databases, but it doesn't really matter. If you don't trust your clients,
you can store your prompts in the app like that:
```python
import redis

import settings


template_storage = redis.from_url(settings.redis_dsn, decode_responses=True)


class Request(BaseModel):
    params: dict
    

@app.post("/ask_language_model/{template_id}")
def generate_response(template_id: str, request: Request):

    template = template_storage.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    
    prompt = Prompt(template)
    ...
```
Also, you might be tempted to instantiate your prompt objects in advance and 
store them in program memory. Such approach, however, will negatively impact
your *adaptability*, unless you implement a sophisticated cache that allows
hot swapping. Keep in mind that the cost of parsing a template string is 
negligible compared to a call to any language model.

# Syntax guide

Promptsub only uses 4 special characters in its basic syntax: `[]{}`. Thanks to
its logic, you can already write elegant and powerful prompts just with that.

If you want even more control over the substitutions, the advanced syntax 
adds 3 characters into the game, which can replace several conditional blocks
of your backend code: `= ~ |`.

## Basic syntax
### Variables
This is a **Variable**: `{name}`.
If we provide a value for it, it will get substituted. If we don't, we will
get an empty string:

`{name}`

| params           | result |
|------------------|--------|
| {"name": "John"} | John   |
| {"age": "26"}    |        |
| {}               |        |

Obviously, the whole point is to insert Variables into some "fixed" text.
That text is called a **Template**. Here's a simple one: 

`Say hello to`

| params           | result       |
|------------------|--------------|
| {"name": "John"} | Say hello to |

Not very useful? Perhaps, but it teaches us that a Template may have zero or 
more Variables. 

Now, if we add a Variable to our Template, things start to get 
interesting:

`Say hello to {name}`

| params           | result            |
|------------------|-------------------|
| {"name": "John"} | Say hello to John |
| {"age": "26"}    |                   |
| {}               |                   |

Expected to see "Say hello to", didn't you? But arguably that wouldn't be a 
nice prompt. If we *suppose* that a Variable may be missing in some parameters,
we should do so *explicitly*. So let's make our Variable optional:

`Say hello to [{name}]`

| params | result       |
|--------|--------------|
| {}     | Say hello to |

Eww, two types of brackets together? Right, doesn't look fancy. The good news
is, you will rarely use it like that. 
### Templates
A Template is a text with some special characters that allow it to 
interact with parameters. Template may contain zero or more Variables, and if 
*any* of them is absent from the parameters, the result will be an empty string.
What about those optional Variables? Well, they do not exist. To render a 
Template, all its Variables are *required* to be in params. But, here's the 
important part:

> Templates **can be nested** inside other templates using the square brackets. 

Let's improve our previous example:

`Say hello [to {name}]`

| params           | result            |
|------------------|-------------------|
| {"name": "John"} | Say hello to John |
| {}               | Say hello         |

What happens here, is that the inner template "to {name}" either becomes 
"to John" or an empty string. 

This simple rule enables us to craft some pretty versatile prompts:

`Write a [{length}] summary about {subject} [in {language}] 
[from the perspective of {author}]`

| params                                              | result                                                                |
|-----------------------------------------------------|-----------------------------------------------------------------------|
| {"subject": "entropy"}                              | Write a summary about entropy                                         |
| {"subject": "the moon landing", "author": "aliens"} | Write a summary about the moon landing from the perspective of aliens |
| {"length": "detailed", "language": "German"}        |                                                                       |

What we achieved here is the following Template hierarchy:  
```
Write a summary about {subject}  
| - {length}  
| - in {language}  
| - from the perspective of {author}
```
The required Variable is "subject", since without it the whole thing would 
become an empty string. The Variables "length", "language" and "author" are 
required for each of their respective Templates, but as these Templates are
nested, we can deal with them becoming empty strings. You can inspect the 
optional and required variables by accessing the ".variables" attribute of a 
prompt as shown [here](#testing-an-advanced-prompt).

To summarize, `This is a template` and `[This is a template]` as well, and they 
are identical. The square brackets are required to mark the boundaries of 
nested Templates, but at the "topmost" level they are optional.

## Advanced syntax
### Multiple Template options
Sometimes we want to significantly change our prompt under certain conditions.
To allow that, a Template may have **alternative options**. This is achieved by
dividing its text with a special **Separator** character - the vertical slash 
"|" by default.

During the substitution the options are evaluated sequentially from left to 
right and the first non-empty result is returned:  

`Examine this picture and [assess the probability of it being taken in {suggested_location} | try to guess where it was taken]`

| params                                       | result                                                                     |
|----------------------------------------------|----------------------------------------------------------------------------|
| {"suggested_location": "Japan"}              | Examine this picture and assess the probability of it being taken in Japan |
| {}                                           | Examine this picture and try to guess where it was taken                   |

Let's not forget that the "top level" sentences are still Templates, so this is 
also valid:

`Say hello to {name} | Ask the speaker's name`

| params           | result                 |
|------------------|------------------------|
| {"name": "John"} | Say hello to John      |
| {"age": "26"}    | Ask the speaker's name |

### Muted Variables
There are situations where the presence of a Variable is important, but its
value is not. Let's say, we want to give an informal greeting to our known
users *without* mentioning their name. 
```python
if "name" in params:
    template = "Hey, mate! What's up?"
else:
    template = "Hello, sir, how can I help?"
```
Yeah, this will work, but now your app needs to know about some template, which:
a) might have been written by someone else; b) could require changes tomorrow.
Well, promptsub got you covered:

`Hey, {~name} mate! What's up? | Hello, sir, how can I help?`

| params           | result                      |
|------------------|-----------------------------|
| {"name": "John"} | Hey, mate! What's up?       |
| {}               | Hello, sir, how can I help? |

If you simply start your Variable with a tilde "~", then it will behave almost 
like a normal one, meaning it will still make its Template an empty sring if
there is no value for it. But if a value *is* provided, it just gets ignored,
and our muted Variable gets "successfuly" replaced with nothing.

As you may guess, there's no difference in where to place muted Variables in 
your Template. In fact, since there may be multiple of them, *sometimes* it will
make a Template more readable if we place them in the beginning. Suppose we 
realized that our informal greeting is too much for people of whom we only know 
their name. We decide, that a true friend is someone who trusts us with his
secrets. Alright:

`{~name} {~bank_account} Hey there, King Midas! | Hello, sir, how can I help?`

Another example:

`Shall I book you a dinner place? [ {~address} | Where did you stay? ]`

| params                                                 | result                                               |
|--------------------------------------------------------|------------------------------------------------------|
| {"address": "1600 Pennsylvania Avenue NW, Washington"} | Shall I book you a dinner place?                     |
| {}                                                     | Shall I book you a dinner place? Where did you stay? |

### Comparing Variable values
The conditionals based on the presence of a Variable in parameters are simple
and powerful. Yet they are limited.
Consider this prompt:

`Remind the user to not forget the umbrella`

It would be a silly thing to write if there is no rain in the forecast, right?
Let's try to optimize this template with conditionals. Our first idea might be:

`{~is_rainy} Remind the user to not forget the umbrella`

| params                | result                                             |
|-----------------------|----------------------------------------------------|
| {"is_rainy": "true"}  | Remind the user to not forget the umbrella         |
| {"is_rainy": "false"} | Remind the user to not forget the umbrella         |

Yikes! Looks like now our condition should not only depend on the *presence* of
the Variable, but also on its *value*.
Luckily, this is possible:

`{~is_rainy=true} Remind the user to not forget the umbrella`

| params                | result                                     |
|-----------------------|--------------------------------------------|
| {"is_rainy": "true"}  | Remind the user to not forget the umbrella |
| {"is_rainy": "false"} |                                            |

If we add an equal sign to a Variable, it effectively splits one into a key
(the text before it) and a value (the text after). Such Variable will only get
substituted in the case of presence of an identical key-value pair in the
parameters. This works for both the muted (the example above) and regular 
Variables:

`Remind the user to not forget the umbrella because it's {weather=rainy}`

| params               | result                                                        |
|----------------------|---------------------------------------------------------------|
| {"weather": "rainy"} | Remind the user to not forget the umbrella because it's rainy |
| {"weather": "sunny"} |                                                               |

`{~length=short} Be as consice as possible | Make the story {length=long}, I will tip`

| params              | result                          |
|---------------------|---------------------------------|
| {"length": "rainy"} | Be as consice as possible       |
| {"length": "long"}  | Make the story long, I will tip |


## Syntax rules
There are few, but they are important:

| rule                                                           | requirements                                                                      |
|----------------------------------------------------------------|-----------------------------------------------------------------------------------|
| Names (keys) of Variables                                      | Non-empty strings of ascii letters, digits and underscores                        |
| Values of Variables used for comparison (written in Templates) | Non-empty strings of any characters, except for the basic syntax specials: `[]{}` |
| Values of Variables provided in parameters                     | Non-empty strings of any characters; integers or floats                           |
| Variable mute character                                        | May only be the first character inside a variable                                 |

Also, you will be happy to know that the number of Variables, Template options 
and the depth of Template nesting are only limited by your conscience.

# Caveats
### Watch your values
`Say hello to {name}`

| params                     | result                      |
|----------------------------|-----------------------------|
| {"name": "null"}           | Say hello to null           |
| {"name": "some bad words"} | Say hello to some bad words |
| {"name": ""}               |                             |

### Don't create unreachable options
If your Template has multiple options, the one with no Variables will always be
valid. Therefore, you should put it last.
Incorrect: `Ask the user's name | Greet {name}`

| params           | result              |
|------------------|---------------------|
| {"name": "John"} | Ask the user's name |

### Mind the default whitespace reduction
Whitespaces and newlines can make your raw templates more readable. But 
language models mostly don't care about them. Also, when testing your 
prompts with different parameters, you probably don't want to see the extra 
spaces. 

That's why **by default** promptsub will postprocess the result of
parameter substitution to remove any leading, trailing or repeated whitespace 
characters, including '\t', '\n', '\r', '\f', '\v' etc.

However, there might be exceptions to this, so you can turn it off if you like:
```python
template = "Continue the conversation: {text}"
prompt = Prompt(template)

text = """
- Also, you know what they call a Quarter Pounder with Cheese in Paris?
- They don't call it a Quarter Pounder with Cheese?
"""
params = {"text": text}

prompt.substitute(params)
# Continue the conversation: - Also... - They...

prompt.substitute(params, postprocess_whitespace_reduction=False)
# Continue the conversation: 
# - Also...
# - They...
```

### Trust your templates
Make sure that all your templates get [tested](#testing-an-advanced-prompt) 
with diverse sets of parameters before being used in production. 

# Possible improvements
A.k.a. current limitations. Listed in an arbitrary order, these are just the
ideas for future work without a concrete roadmap. Suggested implementations seem 
to be backward compatible with the current syntax. However, they are likely to
change the output format of the "Prompt.variables" method. 

Breaking changes are not ruled out in the future, so pay attention to the 
versioning.

### Multiple Variable options - not implemented
It's not hard to imagine a situation where one Variable may serve as an 
alternative to the other. Let's say, that we want to address a user either by 
his *nickname* or by his *first name*, and if nether is awailable ask him
for an intruducion. Right now it would look like this:

`Hello, {user_nickname}! | Hello, {user_firstname}! | Hey! What's your name?`

This simple repetition looks tolerable. But if we had a longer Template or more 
"interchangable" Variables, then we would end up with a sprawling string, which
would be hard to read and error-prone.

A possible solution would be to add the support for multiple options for 
Variables, just like in Templates: "{user_nickname | user_firstname}". It would
require considering the compatibility with mute and comparison symbols. Also,
in such case the whitespaces should probably be allowed at certain positions 
inside Variables for a better readability.

### Data structures as Variables - not implemented
Notice how in the previous example we had the variables `{user_nickname}` and
`{user_firstname}`. In the real world, these are most likely to be not the 
separate key-value pairs, but the attributes of an object `user`. Which means,
that at some point in your app you have to do something like this:
```python
params = {
    "user_firstname": request.params.user.firstname,
    "user_nickname": request.params.user.nickname,
}

result = prompt.substitute(params)
```
Whereas a much better approach would be:
```
result = prompt.substitute(request.params.model_dump())
```
In order for this to work, we need promptsub to access the attributes of 
provided objects. The simplest syntax would be the dot notation: 
"{user.firstname}". Some validation would need to take place.

### Lists and other iterables (except strings) as values - not implemented
Going back to the [movie recomendation prompt](#testing-an-advanced-prompt), 
one may suggest that in order to improve the accuracy, we should include a list 
of user's highly appraised titles instead of just referencing a single one.
Albeit possible, the current solution would be more of a hack, which (you 
guessed it) makes the app interfere in the parameters:
```python
user_favourite_titles = [
    'The Good, the Bad and the Ugly (1966)',
    'Rio Bravo (1959)', 
    'Blow Out (1981)', 
    'Taxi Driver (1976)',
]

template = "Recommend a movie to the user, who is a fan of {favourite_titles}"

params = {"favourite_titles": ", ".join(user_favourite_titles)}
```
Supporting iterables as parameter values would demand careful consideration 
regarding their validation, comparison and formatting.  

### More comparison operators - not implemented
Arguably, the introduction of additional operators for value comparison (such 
as <, >, != or "in") would do more good for functionality than harm 
to simplicity because:
1. It would relocate even more logic from the application to templates, 
which is good. Conditions like "{weekday<5}" or "{travel_distance>1.0}" could
be useful for plenty of tasks;
2. Such syntax would not affect the users who are satisfied with the basics.

The implementation would take a fair amount of work on the "Variable" module. 
It should be considered upon necessity. 
