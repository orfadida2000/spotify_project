import inspect


def err_msg(msg: str) -> str:
    curr_frame = inspect.currentframe()
    caller = curr_frame.f_back if curr_frame is not None else None  # Should never be None
    if caller is None:
        return f"<unknown>: {msg}"  # Should not happen
    code = caller.f_code
    locals = caller.f_locals
    if "self" in locals:
        self_obj = locals["self"]
        return f"{type(self_obj).__name__}.{code.co_name}: {msg}"
    elif "cls" in locals:
        cls_obj = locals["cls"]
        return f"{cls_obj.__name__}.{code.co_name}: {msg}"
    return f"{code.co_name}: {msg}"
