import re
def unbalanced(expr):
    return len(re.findall(r"(?<!\)'", expr)) % 2 == 1

BROKEN = "tr('A truck's job cannot be changed after it is created.')"
FIXED  = "tr('The job of a truck cannot be changed after it is created.')"
ESCAPED = "tr('The driver\'s shift comes with his info.')"

print('broken  -> unbalanced:', unbalanced(BROKEN),
      '| apostrophe-between-letters:', bool(re.search(r"[A-Za-z]'[A-Za-z]", BROKEN)))
print('fixed   -> unbalanced:', unbalanced(FIXED),
      '| apostrophe-between-letters:', bool(re.search(r"[A-Za-z]'[A-Za-z]", FIXED)))
print('escaped -> unbalanced:', unbalanced(ESCAPED),
      '| apostrophe-between-letters:', bool(re.search(r"[A-Za-z]'[A-Za-z]", ESCAPED)))
