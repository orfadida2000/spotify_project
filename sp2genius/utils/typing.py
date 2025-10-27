from enum import StrEnum


class ReturnCode(StrEnum):
    SUCCESS = ""
    GENERAL_ERROR = "An OS error occurred"
    NOT_FOUND = "The specified path does not exist"
    NOT_FILE = "The specified path does not point to a file"
    NOT_DIR = "The specified path does not point to a directory"
    NOT_READABLE_FILE = "The specified file is not readable"
    NOT_READABLE_DIR = "The specified directory is not readable"
    NOT_WRITABLE_FILE = "The specified file is not writable"
    NOT_WRITABLE_DIR = "The specified directory is not writable"
    PERMISSION_DENIED = "The path is not accessible due to permission error"
    TILDE_RESOLVE_FAILED = "Failed to resolve '~' or '~user' in the specified path"
    NAME_TOO_LONG = "The specified path is too long"
    SYMLINK_LOOP = "A symbolic link loop was detected in the specified path"
    EMPTY_PATH = "The specified path is an empty string"
    NON_DIR_COMPONENT = "A component of the specified path is not a directory"
