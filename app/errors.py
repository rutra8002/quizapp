from flask import render_template


_ERROR_COPY = {
    400: "The request could not be processed. Please check your input and try again.",
    401: "You need to log in to access this page.",
    403: "You do not have permission to access this page.",
    404: "We could not find the page you were looking for.",
    405: "That action is not allowed for this page.",
    500: "Something went wrong on our side. Please try again shortly.",
}


def register_error_handlers(app):
    def render_http_error(error):
        status_code = getattr(error, "code", 500)
        title = getattr(error, "name", "Unexpected Error")
        description = _ERROR_COPY.get(status_code) or getattr(
            error, "description", "An unexpected error occurred."
        )
        return (
            render_template(
                "error.html",
                status_code=status_code,
                title=title,
                description=description,
            ),
            status_code,
        )

    for status_code in (400, 401, 403, 404, 405, 500):
        app.register_error_handler(status_code, render_http_error)

