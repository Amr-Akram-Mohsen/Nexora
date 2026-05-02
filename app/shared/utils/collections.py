def my_zip(*iterables):
    """
    Custom zip function that handles iterables of different lengths by grouping the remainder.
    """
    my_list = []
    if not iterables:
        return my_list
    
    # We assume iterables[0] exists and we use it as the primary length
    primary = iterables[0]
    secondary = iterables[1] if len(iterables) > 1 else []

    for i, val in enumerate(primary):
        if i == len(primary) - 1 and i < len(secondary) - 1:
            my_list.append((val, secondary[i:]))
        elif i < len(secondary):
            my_list.append((val, secondary[i]))
        else:
            # Fallback if secondary is shorter
            my_list.append((val, None))
    return my_list
