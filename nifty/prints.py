def print_banner():
    banner = """
                d8,   ,d8888b
               `8P    88P'      d8P
                   d888888P  d888888P
      88bd88b   88b  ?88'      ?88'  ?88   d8P
      88P' ?8b  88P  88P       88P   d88   88
     d88   88P d88  d88        88b   ?8(  d88
    d88'   88bd88' d88'        `?8b  `?88P'?8b
                                            )88
                                           ,d8P
                                       `?8888P'
    """
    print(banner)


def print_demo_message():
    demo_message = f'''
    {'-'*40}
    # NIFTY DEMO MODE
    # Working with synthetic spectrum.
    # Start with "-h" to get available options.
    {'-'*40}
    '''
    print(demo_message)


def print_summary_of_input_parameters(args):
    summary_of_input_parameters = f'''
    {'-'*40}
    # NIFTY INPUT PARAMETERS
    # Input: {args.input}
    # Type: {args.type}
    # X-Key: {args.xkey}
    # Y-Key: {args.ykey}
    # Features: {args.features}
    # Reference spectrum: {args.ref}
    # Stellar lines: {args.stellar}
    # Matching: {args.matching}

    {'-'*40}
    '''
    print(summary_of_input_parameters)


def print_navigation_keyboard_shortcuts():
    navigation_keyboard_shortcuts = f'''
    {'-'*40}
    # NAVIGATION KEYBOARD SHORTCUTS
    #         r  reset plots
    #      left  jump to next feature
    #     right  jump to previous feature
    #        up  shift the reference spectrum up
    #      down  shift the reference spectrum down
    #    alt+up  shift the stellar reference lines up
    #  alt+down  shift the stellar reference lines down
    #         +  zoom into feature by decreasing range around feature
    #         -  zoom out feature by increasing range around feature
    #         m  mark / unmark current measurement
    #         n  add note to measurement in command line prompt
    # backspace  delete last measurement
    #  spacebar  save measurements
    #    escape  exit NIFTY
    {'-'*40}
    '''
    print(navigation_keyboard_shortcuts)
