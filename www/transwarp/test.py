

item_count = 4
page_size = 2
a = item_count // page_size + (1 if item_count % page_size > 0 else 0)
print a