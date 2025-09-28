# transferdepot
a file transfer service. We split it into three doors — a UI for people, an API for automation, and an Admin panel for health checks — and then moved file downloads out of the app entirely so they’re served directly by Nginx. That way, the app only does logic, and the web server does the heavy lifting for big transfers. 
