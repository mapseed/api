Create users from frontend
===

Create Users from Frontend
--------------------------

We add a new endpoint to create users from frontend `https://<your-host>/api/v2/users/new`

You need to use a POST request this is a AJAX example

```javascript
const json = {username: "asdasd", "password1": "password"}
const response = await fetch(
        `${apiRoot}users/new?format=json`, {
            headers: {
                "Content-Type": "application/json",
            },
            credentials: "include",
            method: "POST",
            body: json,
        },
    );
```

Backend
-------

In the backend you can add two new settings to decide what is the default dataset and GRoup to set to new created users from frontend.

local_settings.py

```python
DEFAULT_REGISTER_DATASET="quepasa-input"
DEFAULT_REGISTER_GROUP="administrators"
```