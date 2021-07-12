# ~\~ language=Python filename=entangled/pymd/__init__.py
# ~\~ begin <<lit/pymd.md|pymd>>[0]
__all__ = ["format", "validator"]
# ~\~ end
# ~\~ begin <<lit/pymd.md|pymd>>[1]
def format(source, language, css_class, options, md, classes=None, id_value='', attrs=None, **kwargs):
    patched_source = source \
        .replace("<", "&lt;") \
        .replace(">", "&gt;")
    code_block = "<pre><code class={}>{}</code></pre>".format(language, patched_source)
    ann = "<div class=\"lp-fragment\"><div class=\"lp-ref\" id=\"lp-{}\">{}</div>{}</div>"
    if "file" in options:
        id = options["file"]
        name = "«file://{}»".format(id)
        return ann.format(id, name, code_block)
    elif "id" in options:
        id = options["id"]
        name = "«{}»".format(id)
        return ann.format(id, name, code_block)
    return code_block
# ~\~ end
# ~\~ begin <<lit/pymd.md|pymd>>[2]
def validator(language, inputs, options, attrs, md):
    if 'id' in inputs: 
        options['id'] = inputs['id']
    elif 'file' in inputs:
        options['file'] = inputs['file']
    else:
        return False
    return True
# ~\~ end
