"""
python specific utilities/helpers (no Django involved)
"""

def parse_tag_args(token):
    """
    returns a dict of args passed in to a template tag
    'k1=v1 k2 k3=v3' => {k1:v1, k2:True, k3:v3}
    """
    args = {}
    raw_args = token.split_contents()
    for raw_arg in raw_args:
        if "=" in raw_arg:
            k,v = raw_arg.split("=")
            args[k] = v
        else:
            args[raw_arg] = True

    return args

