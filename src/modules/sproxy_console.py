from termcolor import colored

def pmsg(msg):
    print(colored('>>>', 'cyan'), colored(msg, 'green'))

def perr(msg):
    print(colored('>>>', 'red'), colored(msg, 'green'))