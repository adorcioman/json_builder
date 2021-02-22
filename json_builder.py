import json
import abc
import re


class NotSet(abc.ABC):
    # Class used for unset values
    pass


class IComponent(abc.ABC):
    __slots__ = ["key"]

    @abc.abstractmethod
    def add(self, root, component_next, value: object = NotSet):
        """
        Abstract method. Any component must implement this method
        :param root: root json object
        :param component_next: next path component
        :param value: json path value
        :return: new root json object
        """
        pass


class ComponentKey(IComponent):
    def __init__(self, key: str):
        self.key = key

    def add(self, root, component_next: IComponent, value: object = NotSet):
        """
        Add key to dictionary
        :param root: root dictionary
        :param component_next: next component to process (used to check the type)
        :param value: value to add  (default: NotSet())
        :return: updated dictionary
        """

        if not isinstance(root, dict):
            raise TypeError(f"Can't insert key \"{self.key}\", object is not a dictionary")

        if self.key == "$":
            # Skip component, return the same root object
            return root

        if not isinstance(value, NotSet):
            # If value is provided, set it
            root[self.key] = value
            return root

        if self.key not in root:
            # key doesn't exist, initialize object
            if isinstance(component_next, ComponentIndex):
                root[self.key] = []
            else:
                root[self.key] = {}

        root = root[self.key]
        return root


class ComponentIndex(IComponent):

    def __init__(self, key: str):
        # Cast key into an list index
        self.key = int(key)

    def add(self, root, component_next: IComponent, value: object = NotSet):
        """
        Add new list element
        :param root: root list
        :param component_next: next component to process (used to check the type)
        :param value: value to add (default: NotSet())
        :return: updated list
        """

        if not isinstance(root, list):
            raise TypeError(f"Can't insert on position \"{self.key}\", object is not a list")

        if len(root) < self.key:
            raise IndexError(f"Index to big \"{self.key}\", previous list indexes not defined")

        if len(root) == self.key:
            # Create new index with a default object
            root.append(NotSet())

        if not isinstance(value, NotSet):
            # If value is specified, overwrite existing value
            root[self.key] = value
        elif isinstance(component_next, ComponentKey):
            # Next component is an dictionary key, initialize with an empty dict
            root.append({})
        else:
            # Next component is an list index, initialize with an empty list
            root.append([])

        root = root[self.key]  # Go one level deeper
        return root


class JsonBuilder:

    @staticmethod
    def __check_json(root: object):
        """
        Check if object is json valid

        :param root: json object
        :return: None
        """
        try:
            json.dumps(root)
        except TypeError:
            raise TypeError(f"Object {root} is not JSON serializable.")

    @staticmethod
    def __check_path(json_path: str):
        """
        Check if the json path match a specific format

            ^\$: Any expression must start with "$"
            (\.[a-zA-Z0-9]+)*: match dictionary keys
            (\[[0-9]+\])+)*: match list indexes

        :param json_path: json path expression
        :return: None
        """
        json_path_regex = r"^\$((\.[a-zA-Z0-9]+)*((\[[0-9]+\])+)*)*"
        if not re.fullmatch(json_path_regex, json_path):
            raise ValueError(f"Invalid json path \"{json_path}\". "
                             f"Check https://goessner.net/articles/JsonPath/ for more details.")

    @staticmethod
    def __get_path_components(json_path: str):
        component_list = []

        for item in json_path.split("."):
            if re.fullmatch(r"[0-9a-xA-X\$]+\[.*\]$", item):  # Match list indexes
                key, indexes = re.match(r"([0-9a-xA-X\$]+)(\[.*\])$", item).groups()
                component_list.append(ComponentKey(key))
                component_list.extend([ComponentIndex(value) for value in re.findall(r"\d+", item)])
            else:
                component_list.append(ComponentKey(item))

        return component_list

    @staticmethod
    def add(root: object, json_path: str, value: object):
        """
        Incrementally build a json object

        :param root: existing json object
        :param json_path: location where the value is added
        :param value: value to add
        :return: updated json object
        """
        JsonBuilder.__check_json(root)
        JsonBuilder.__check_path(json_path)
        JsonBuilder.__check_json(value)

        component_list = JsonBuilder.__get_path_components(json_path)
        component_iter = iter(component_list)
        component_current, component_next = next(component_iter, None), next(component_iter, None)

        child = root  # Preserve the root reference
        while component_current:
            # Set the value only for the last component
            component_value = NotSet() if component_next else value

            try:
                child = component_current.add(child, component_next, component_value)
            except TypeError as error:
                raise TypeError(f"{error}. Root: {root}. Json path: {json_path}")

            # Go to the next path component
            component_current = component_next
            component_next = next(component_iter, None)

        return root
