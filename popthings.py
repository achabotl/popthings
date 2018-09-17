"""
Import a TaskPaper document with projects as Things projects.

The script supports placeholder replacement, headers and checklist
items. Date parsing is done by Things itself, so anything Things
supports is also supported here.

- The indentation _must_ be done with Tabs.
- Placeholders are on the second line of file, use a '$' prefix,
  and are space-separated.
- The @start and @due tags expect a value and will be used for the
  "when" and "deadline" attributes of a project of task. All other
  tags are passed through and their values are ignored.
- A project under a project is a considered a heading. It can't have
  notes. Tasks under it can be indented or not, which is more flexible
  than the TaskPaper format.
- A task under a task is a checklist item.

Here's an example TaskPaper file containing two projects demonstrating
what's possible. They would be added to Things as two separate projects.

    Project 1:
        $due $start $where
        Note under project 1
        - Task 1 @due($start + 1w) @$where
            A note under task 1
        - Task 2 @start($start)
            - Checklist item under task 2
                - Also a checklist item under task 2
        Heading 1:
            - Task under heading 1

    Project 2:
        - Task under project 2
        Heading 2, under project 2:
        - Task under heading 2


Attributes
----------

"""
from io import open
import json
import logging
import re
import sys
try:
    # Python 3
    from urllib.parse import quote
except ImportError:
    # Python 2
    from urllib import quote
import webbrowser
try:
    # Shadow Python 2 input, which is eval(raw_input(prompt))
    input = raw_input
except NameError:
    # Python 3
    pass


__version__ = "1.0.0"

log = logging.getLogger(__name__)

# Mapping between tag names in TaskPaper, and names in the Things
# JSON API. The format is {taskpaper_name: things_name}
SPECIAL_TAGS_MAPPING = {
    'due': 'deadline',
    'start': 'when',
}

# Default placeholder symbol
PLACEHOLDER_SYMBOL = '$'

PATTERN_PROJECT = re.compile(r'^(?P<indent>\t*)(\s*)(?P<text>(?<!-\s).*):$')
PATTERN_TASK = re.compile(r'^(?P<indent>\t*)(-\s(?P<text>.*))$')
PATTERN_NOTE = re.compile(r'(?P<indent>\t*)(?P<text>[^\t]*.*)$')
PATTERN_TAG = re.compile(r"""(?:^|\s+)@             # space and @ before tag
                             (?P<name>\w+)          # the tag name
                             (?:\(                  # don't capture the ()
                                 (?P<value>[^\)]*)  # the tag value, if any
                                 \)                 # close the () pair
                                 )?                 # the value is optional
                             (?=\s|$)               # lookahead, match if
                                                    # space or EOL
                             """, re.VERBOSE)


class TPNode(object):
    def __init__(self, line, text, indent, type, line_number=None, tags=None):
        """
        A node of the TaskPaper document tree.

        Parameters
        ----------
        line : str
            Entire content of the line, including.
        text : str
            Text of the line, excluding tags, '- ' prefix, or trailing ':'
        indent : int
            Indent level
        type : str
            Type of the line. One of 'project', 'task', 'note', or 'empty'.
        line_number : int
        tags : list of tuples
            List of (tag_name, tag_value) tuples.
        """
        self.line = line
        self.text = text
        self.indent = indent
        self.type = type
        self.line_number = line_number
        self.tags = tags if tags is not None else []
        self.parent = None
        self.children = []

    def __repr__(self):
        return ('TPNode({self.text!r}, type={self.type!r},'
                'tags={self.tags}, indent={self.indent})').format(
            self=self)

    @classmethod
    def from_line(cls, line, line_number=None):
        """
        Parse a line of text and create a TPNode based on the line format.

        Parameters
        ----------
        line : str
            The content of the line.
        line_number : int (optional)
            The line number.

        Returns
        -------
        node : TPNode

        """
        text_without_tags, tags_text = cls.split_text_and_tags(line)
        tags = cls.find_tags(tags_text)

        match = PATTERN_TASK.match(text_without_tags)
        if match:
            type = 'task'
        else:
            match = PATTERN_PROJECT.match(text_without_tags)
            if match:
                type = 'project'
            else:
                match = PATTERN_NOTE.match(text_without_tags)
                if match:
                    type = 'note'
                else:
                    type = 'empty'
        indent = len(match.group('indent'))
        text = match.group('text')
        return TPNode(line, text, indent, type, line_number, tags=tags)

    @classmethod
    def split_text_and_tags(cls, line):
        """
        Split the task/project text from the tags at the end of the line.

        Parameters
        ----------
        line : str
            A line of text with tags.

        Returns
        -------
        text_without_tags : str
            Text stripped from tags.
        tags_text : str
            Text containing tags.

        """
        text_without_tags, sep, tags_text = line.partition(' @')
        if sep:
            text_without_tags = text_without_tags.rstrip()
        return text_without_tags, sep + tags_text

    def add_child(self, node):
        """
        Add a child to the current node.

        Parameters
        ----------
        node : TPNode
            The node to add as a child.

        """

        node.parent = self
        self.children.append(node)

    def is_project(self):
        """ True is the node is of type 'project'. """
        return self.type == 'project'

    def is_task(self):
        """ True is the node is of type 'task'. """
        return self.type == 'task'

    def is_note(self):
        """ True is the node is of type 'note'. """
        return self.type == 'note'

    def is_empty(self):
        """ True is the node is of type 'empty'. """
        return self.type == 'empty'

    def is_root(self):
        """ True if the node is the root of the TaskPaper tree. """
        return self.type == 'root'

    def flatten(self):
        """
        Flattens the tree, essentially recreating the document.

        Iterating over the output gives you one line at a time.

        Returns
        -------
        nodes : list of TPNodes

        """
        flattened = [self] if self.type != 'root' else []
        for child in self.children:
            flattened.extend(child.flatten())
        return flattened

    def has_project_parent(self):
        """
        Returns True if the current task as a parent of type 'project'.

        Returns
        -------
        project_parent : bool

        Note
        ----
        This is not part of the usual Tree API, but it's useful to
        identify 'project' nodes that are Things Headers.

        """
        parent = self.parent
        if parent is None:
            return False
        while not parent.is_project():
            if parent.is_root():
                return False
            parent = parent.parent
        return True

    @staticmethod
    def find_tags(text):
        """
        Parse the tags out of the text.

        Parameters
        ----------
        text : str
            Line text to parse for tags.

        Returns
        -------
        tags : list of tuples
            List of (tag_name, tag_value) tuples. If the tag has no
            value, the tag_value is None.

        """
        tags = []
        for tag in PATTERN_TAG.finditer(text):
            tags.append((tag.group('name'), tag.group('value')))
        return tags


class ThingsObject(object):
    #: Things item type
    type = None

    def __init__(self, title):
        """
        Abstract base class for all Things objects, and factory to create
        them.

        Use `from_tp_node` to create ThingsObjects from TaskPaper TPNode
        object.

        Parameters
        ----------
        title : str
            The object's text.

        Attributes
        ----------
        type : str, {project, to-do, checklist-item, header, note'}
            The Things type, used for exporting to JSON.

        """

        self.title = title
        # Mapping between Python attribute names and JSON keys.
        self._attrs_mapping = {}

    def __repr__(self):
        args = ', '.join('{k}={v!r}'.format(k=k, v=v)
                         for k, v
                         in self.__dict__.items()
                         if not k.startswith('_')
                         )
        return "{self.__class__.__name__}({args})".format(
            self=self, args=args)

    @classmethod
    def from_tp_node(self, node):
        """
        Factory function to create a Things object from a Taskpaper
        TPNode object.

        The exact type of the object returned depends on TPNode.type.

        Parameters
        ----------
        node : TPNode

        Returns
        -------
        item : Things object

        """
        self.node = node
        special_tags, regular_tags = self._split_special_tags(node.tags)
        special_tags_dict = {name: value for name, value in special_tags}
        tags_str = [name for name, value in regular_tags]
        if self.is_project(node):
            return ThingsProject(node.text, tags=tags_str, **special_tags_dict)
        elif self.is_heading(node):
            return ThingsHeading(node.text)
        elif self.is_todo(node):
            return ThingsToDo(node.text, tags=tags_str, **special_tags_dict)
        elif self.is_checklist_item(node):
            return ThingsChecklistItem(node.text)
        elif self.is_note(node):
            return ThingsNote(node.text)
        else:
            raise ValueError("Node type not recognised.", node)

    @staticmethod
    def _split_special_tags(tags):
        """
        Splits tags into two groups, the Things tags with special
        meaning, such as 'due' and 'start', and the other ones.

        Parameters
        ----------
        tags : list of tuples
            List of (tag_name, tag_value) tuples.

        Returns
        -------
        special_tags : list of tuples
        regular_tags : list of tuples

        """
        special_tags = []
        regular_tags = []
        for name, value in tags:
            if name in SPECIAL_TAGS_MAPPING:
                special_tags.append((SPECIAL_TAGS_MAPPING[name], value))
            else:
                regular_tags.append((name, value))
        return special_tags, regular_tags

    @staticmethod
    def is_heading(tp_node):
        """ True if the TPNode is a Things heading. """
        return tp_node.is_project() and tp_node.has_project_parent()

    @staticmethod
    def is_project(tp_node):
        """ True if the TPNode is a Things project. """
        return tp_node.is_project() and not tp_node.has_project_parent()

    @staticmethod
    def is_checklist_item(tp_node):
        """ True if the TPNode a Things checklist item. """
        return tp_node.is_task() and tp_node.parent.is_task()

    @staticmethod
    def is_todo(tp_node):
        """ True if the TPNode is a Things to-do item. """
        return tp_node.is_task() and not tp_node.parent.is_task()

    @staticmethod
    def is_note(tp_node):
        """ True if the TPNode is a Things note. """
        return tp_node.is_note() or tp_node.is_empty()

    def to_json(self):
        """
        Convert the object and its children to a JSON object following
        the Things JSON schema.

        Returns
        -------
        d : dict

        """
        d = {
            'type': self.type,
            'attributes': {
                'title': self.title,
            }
        }
        for obj_attr, things_attr in self._attrs_mapping.items():
            value = getattr(self, obj_attr)
            if value:
                d['attributes'][things_attr] = value
        return d


class _ThingsRichObject(ThingsObject):

    def __init__(self, title, notes='', when=None, deadline=None, tags=None):
        """
        Private Things object that has nodes, when date, deadline, and tags.

        Parameters
        ----------
        title : str
            The object's text.
        notes : str
            Notes for that object.
        when : str
            Date or date+time for the object's "start" date.
        deadline : str
            Date or date+time for the object's deadline date.
        tags : list of str
        """
        super(_ThingsRichObject, self).__init__(title)
        self.notes = notes
        self.when = when
        self.deadline = deadline
        if tags is None:
            tags = []
        self.tags = tags
        # Mapping between Python attribute names and JSON keys.
        attrs_mapping = {
            'notes': 'notes',
            'when': 'when',
            'deadline': 'deadline',
            'tags': 'tags',
        }
        self._attrs_mapping.update(attrs_mapping)

    def add_note(self, node):
        """
        Append node.title to the current item's note.

        Parameters
        ----------
        node : TPNode
            Node containing the note's text.

        """
        if self.notes:
            note_text = '\n{node.title}'.format(node=node)
        else:
            note_text = node.title
        self.notes += note_text


class ThingsToDo(_ThingsRichObject):
    type = 'to-do'

    def __init__(self,
                 title,
                 notes='',
                 when=None,
                 deadline=None,
                 tags=None,
                 checklist_items=None):
        """
        Represent a to-do item in Things.

        Can be exported to a JSON object with the to_json method to use
        with the Things URL scheme.

        Parameters
        ----------
        title : str
            Text of the to-do item.
        notes : str
            Note text.
        when : str
            Defer date, or start date for the to-do item.
        deadline : str
            Deadline fo the to-do item.
        tags : list of str
            List of tag names.
        checklist_items : list of str
            List of checklist-item text.

        """
        super(ThingsToDo, self).__init__(
            title, notes=notes, when=when, deadline=deadline, tags=tags)
        if checklist_items is None:
            checklist_items = []
        self.checklist_items = checklist_items

    def add_checklist_item(self, node):
        """
        Add checklist item to this to-do item.

        Parameters
        ----------
        node : ThingsObject

        """
        self.checklist_items.append(node)

    def to_json(self):
        """
        Convert the object and its children to a JSON object following
        the Things JSON schema.

        Returns
        -------
        d : dict

        """
        d = super(ThingsToDo, self).to_json()
        d['attributes']['checklist-items'] = [
            item.to_json() for item in self.checklist_items
        ]
        return d


class ThingsProject(_ThingsRichObject):
    type = 'project'

    def __init__(self,
                 title,
                 notes='',
                 when=None,
                 deadline=None,
                 tags=None,
                 items=None,
                 area=None):
        """
        Things project item.


        Parameters
        ----------
        title : str
            The project name.
        notes : str
            Project notes.
        when : str
            Defer or start date for the project.
        deadline : str
            Project deadline.
        tags : list of str
            List of tag names.
        items: list of {ThingsToDo, ThingsHeading}
            List of items under the current project.
        area : str
            Name of the area under which to create the project.
        """
        super(ThingsProject, self).__init__(
            title, notes=notes, when=when, deadline=deadline, tags=tags)
        if items is None:
            items = []
        self.items = items
        self.area = area
        self._attrs_mapping['area'] = 'area'

    def add_item(self, item):
        """
        Append item to list of items.

        Parameters
        ----------
        item : ThingsObject

        """
        self.items.append(item)

    def to_json(self):
        """
        Convert the object and its children to a JSON object following
        the Things JSON schema.

        Returns
        -------
        d : dict

        """
        d = super(ThingsProject, self).to_json()
        d['attributes']['items'] = [
            item.to_json() for item in self.items
        ]
        return d


class ThingsHeading(ThingsObject):
    """
    Things heading item.

    Parameters
    ----------
    title : str
        Heading name

    """

    type = 'heading'


class ThingsChecklistItem(ThingsObject):
    """
    Things checklist-item object.

    Parameters
    ----------
    title : str
        Checklist item text

    """

    type = 'checklist-item'


class ThingsNote(ThingsObject):
    """
    Things note object.

    Parameters
    ----------
    title : str
        Note text.

    """
    type = 'note'


def find_and_replace_placeholders(text, symbol=PLACEHOLDER_SYMBOL):
    """
    Find and replace placeholders in text.

    Assumes that placeholders are on the second line, and that the
    line starts with the placeholder symbol (ignoring spaces). Returns
    the original text if there are no placeholders.

    Parameters
    ----------
    text : str
        Text of the entire TaskPaper document.
    symbol : str
        Symbol representing placeholder. Default is '$'.

    Returns
    -------
    new_text : str


    Notes
    -----
    Here's a document with placeholders:

        Project:
            $due $start
            - Task @due($due) @start($start)

    """
    lines = text.splitlines()
    placeholder_line = lines[1].strip()
    if not placeholder_line.startswith(symbol):
        # Text without placeholders
        return text

    new_text = '\n'.join(lines[:1] + lines[2:])
    placeholders = [name.strip()
                    for name in placeholder_line.split(symbol)
                    if name]
    for name in placeholders:
        name_prompt = name.capitalize()
        value = input('{} value? '.format(name_prompt))
        new_text = new_text.replace(
            '{symbol}{name}'.format(symbol=symbol, name=name), value)
    return new_text


def things_objects_from_taskpaper_tree(tree):
    """
    Build a list of Things objects from a TPNode tree.

    Parameters
    ----------
    tree : TPNode

    Returns
    -------
    things_nodes : list of ThingsObject

    """
    things_nodes = []
    for tp_node in tree.flatten():
        things_obj = ThingsObject.from_tp_node(tp_node)
        if things_obj.is_project(tp_node):
            # Add as top-level item in the list of things_nodes
            things_nodes.append(things_obj)
            last_things_obj_accepting_notes = things_obj
        elif things_obj.is_todo(tp_node):
            # Add as regular item to most-recent project
            things_nodes[-1].add_item(things_obj)
            last_things_obj_accepting_notes = things_obj
        elif things_obj.is_heading(tp_node):
            # Add as regular item to most-recent project
            things_nodes[-1].add_item(things_obj)
        elif things_obj.is_checklist_item(tp_node):
            # Add to most recent task of most recent project.
            things_nodes[-1].items[-1].add_checklist_item(things_obj)
        elif things_obj.is_note(tp_node):
            last_things_obj_accepting_notes.add_note(things_obj)
    return things_nodes


def build_taskpaper_document_tree(text):
    """
    Build a TaskPaper document tree from a TaskPaper text document.

    Parameters
    ----------
    text : str
        Entire text of the TaskPaper document.

    Returns
    -------
    root : TPNode
        The document root node.

    """
    nodes = [
        TPNode.from_line(line, line_number)
        for line_number, line in enumerate(text.splitlines())
    ]

    root = TPNode('', '', -1, type='root')
    previous_node = root
    for node in nodes:
        if node.indent == previous_node.indent:
            log.debug('Adding {node} to {previous_node.parent}'.format(
                node=node, previous_node=previous_node
            ))
            previous_node.parent.add_child(node)
        if node.indent > previous_node.indent:
            log.debug('Adding {node} to {previous_node}'.format(
                node=node, previous_node=previous_node
            ))
            previous_node.add_child(node)
        if node.indent < previous_node.indent:
            log.debug('{node} is aunt of {previous_node}'.format(
                node=node, previous_node=previous_node
            ))
            # Find the parent whose indent difference is 1 and add sister
            previous_parent = previous_node
            while node.indent <= previous_parent.indent:
                previous_parent = previous_parent.parent
            log.debug('Adding {node} to {previous_parent}'.format(
                node=node, previous_parent=previous_parent
            ))
            previous_parent.add_child(node)
        previous_node = node
    return root


def taskpaper_template_to_things_json(text):
    """
    Parse TaskPaper document into a list of Things JSON objects.

    Parameters
    ----------
    text : str
        Entire test of the TaskPaper template.

    Returns
    -------
    out : list of JSON objects

    """
    tree = build_taskpaper_document_tree(text)
    things_objs = things_objects_from_taskpaper_tree(tree)
    return [item.to_json() for item in things_objs]


def build_things_url(things_json):
    """
    Build Things 'things:///json?data=' URL.

    Parameters
    ----------
    things_json : list of dicts

    Returns
    -------
    url : str

    Notes
    -----
    See this document fo the URL spec.
    https://support.culturedcode.com/customer/en/portal/articles/2803573

    """
    json_str = json.dumps(things_json, separators=(',', ':'))
    url = 'things:///json?data={}'.format(quote(json_str))
    return url


def get_document(platform):
    """
    Get the document content based on the platform and context.

    If the script is run on iOS from the Share sheet, it captures the
    documents content. If it's run as a standalone script, it opens a
    File picker. If it's running on the Mac, it opens the filepath
    passed in as an argument.

    Parameters
    ----------
    platform : str, {ios, darwin}
        Platform on which the script is running.

    Returns
    -------
    text : str

    """
    if platform == 'ios':
        # If it's on iOS, get the text from the extension and get dates
        # from pop ups.
        import appex
        import dialogs

        if appex.is_running_extension():
            template = appex.get_text()
        else:
            # Running either from the Today widget or from Pythonista
            infile = dialogs.pick_document()
            if infile is None:
                # User cancelled
                sys.exit()
            with open(infile, encoding='utf-8') as f:
                template = f.read()
    else:
        import argparse
        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawTextHelpFormatter,
        )
        parser.add_argument('infile',
                            help='path to taskpaper template')
        args = parser.parse_args()
        with open(args.infile, encoding='utf-8') as f:
            template = f.read()
    return template


def taskpaper_to_things(text):
    """
    Main function to parse a TaskPaper document and import it into
    Things.

    The function uses the Thing URL scheme to import the project.

    Parameters
    ----------
    text : str
        The TaskPaper document.

    """
    things_json = taskpaper_template_to_things_json(text)
    url = build_things_url(things_json)
    webbrowser.open(url)


def cli():
    logging.basicConfig(level=logging.WARNING)
    template = get_document(sys.platform)
    template = find_and_replace_placeholders(template)
    taskpaper_to_things(template)


if __name__ == "__main__":
    sys.exit(cli())

