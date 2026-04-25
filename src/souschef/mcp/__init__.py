"""MCP server for SousChef.

Thin wrapper around `souschef.models.*`: each MCP tool opens a DB connection,
calls the corresponding model function, auto-logs the call to chat_log, and
returns the result.
"""
