from unittest import TestCase

from popthings import TPNode, ThingsToDo, ThingsProject


template = """
Prepare luggage for $Destination:
	$Destination $date
	- Things to do before leaving
		- Buy Travel insurance
		- Check food recommendations
			- Check - Dinner, drive ins and Dives
				http://www.dinersdriveinsdiveslocations.com
			- Check TV Food Maps
				http://www.tvfoodmaps.com <www.tvfoodmaps.com>
			- Check restaurants in Where Chefs Eat
			- Check NYT 36 hours in XXX

"""


class TestTPNodeTypes(TestCase):

    def test_is_task(self):
        self.assertTrue(TPNode.from_line('- Task').is_task())
        self.assertTrue(TPNode.from_line('\t- Task').is_task())
        self.assertTrue(TPNode.from_line('\t- Task:').is_task())

    def test_is_not_task(self):
        self.assertFalse(TPNode.from_line('-Note').is_task())
        self.assertFalse(TPNode.from_line('-Project:').is_task())

    def test_is_project(self):
        self.assertTrue(TPNode.from_line('Project:').is_project())
        self.assertTrue(TPNode.from_line('\tProject:').is_project())
        self.assertTrue(TPNode.from_line('-Note:').is_project())

    def test_is_not_project(self):
        self.assertFalse(TPNode.from_line('- Task:').is_project())

    def test_is_note(self):
        self.assertTrue(TPNode.from_line('Note').is_note())
        self.assertTrue(TPNode.from_line('-Note').is_note())


class TestTPNodeIndent(TestCase):

    def test_indent(self):
        self.assertEqual(TPNode.from_line('- Task').indent, 0)
        self.assertEqual(TPNode.from_line('\t- Task').indent, 1)
        self.assertEqual(TPNode.from_line('\t\t- Task').indent, 2)
        self.assertEqual(TPNode.from_line(' - Task').indent, 0)
        self.assertEqual(TPNode.from_line('    - Task').indent, 0)


class TestThingsObjectToJson(TestCase):

    def test_task_with_title(self):
        obj = ThingsToDo('Task 1')
        target = {
            'attributes': {
                'title': 'Task 1',
                'checklist-items': [],
            },
            'type': 'to-do'
        }
        self.assertEqual(obj.to_json(), target)

    def test_project_with_title(self):
        obj = ThingsProject('Project')
        target = {
            'type': 'project',
            'attributes': {
                'title': 'Project',
                'items': []
            }
        }
        self.assertEqual(obj.to_json(), target)
