"""The xml_python library.

A library for converting XML into python objects.

Provides the Builder class.
"""

from typing import IO, Any, Callable, Dict, Generic, List, Optional, TypeVar
from xml.etree.ElementTree import Element, ElementTree, fromstring, parse

from attr import Factory, attrib, attrs

__all__: List[str] = [
    'InputObjectType', 'OutputObjectType', 'TextType', 'AttribType',
    'MakerType', 'ParserType', 'NoneType', 'BuilderError', 'UnhandledElement',
    'Builder'
]

InputObjectType = TypeVar('InputObjectType')
OutputObjectType = TypeVar('OutputObjectType')
TextType = Optional[str]
AttribType = Dict[str, str]
MakerType = Callable[[Optional[InputObjectType], Element], OutputObjectType]
ParserType = Callable[[OutputObjectType, Element], None]
NoneType = type(None)


class BuilderError(Exception):
    """Base exception."""


class UnhandledElement(BuilderError):
    """No such parser has been defined."""


@attrs(auto_attribs=True)
class Builder(Generic[InputObjectType, OutputObjectType]):
    """A builder for returning python objects from xml ``Element`` instances.

    Given a single node and a input object, a builder can transform the input
    object according to the data found in the provided element.

    To parse a tag, use the :meth:`~Builder.parse_element` method.

    :ivar ~Builder.maker: The method which will make an initial object for this
        builder to work on.

    :ivar ~Builder.name: A name to differentiate a builder when debugging.

    :ivar ~Builder>parsers: A dictionary of parser functions mapped to tag
        names.

    :ivar ~Builder.builders: A dictionary a sub builders, mapped to tag names.
    """

    maker: MakerType = attrib(repr=False)

    name: Optional[str] = None
    parsers: Dict[str, ParserType] = attrib(default=Factory(dict), repr=False)
    builders: Dict[str, 'Builder'] = attrib(default=Factory(dict), repr=False)

    def build(
        self, input_object: Optional[InputObjectType], element: Element
    ) -> OutputObjectType:
        """Make the initial object, then handle the element.

        If you are looking to build an object from an xml element, this is
        likely the method you want.

        :param input_object: An optional input object for the provided elements
            to work on.

        :param element: The element to handle.
        """
        output_object: OutputObjectType = self.maker(input_object, element)
        self.handle_elements(output_object, list(element))
        return output_object

    def handle_elements(
        self, subject: OutputObjectType, elements: List[Element]
    ) -> None:
        """Handle each of the given elements.

        This method is usually called by the :meth:`~Builder.make_and_handle`
        method.

        :param subject: The object to maniplate with the given elements.

        :param elements: The elements to work through.
        """
        element: Element
        for element in elements:
            tag: str = element.tag
            if tag in self.parsers:
                self.parsers[tag](subject, element)
            elif tag in self.builders:
                builder: Builder[OutputObjectType, Any] = self.builders[tag]
                obj: Any = builder.maker(subject, element, )
                builder.handle_elements(obj, list(element))
            else:
                raise UnhandledElement(self, element)

    def handle_string(self, xml: str) -> OutputObjectType:
        """Parse and handle an element from a string.

        :param xml: The xml string to parse.
        """
        element: Element = fromstring(xml)
        return self.build(None, element)

    def handle_file(self, fileobj: IO[str]) -> OutputObjectType:
        """Handle a file-like object.

        :param fileobj: The file-like object to read XML from.
        """
        return self.handle_string(fileobj.read())

    def handle_filename(self, filename: str) -> OutputObjectType:
        """Return an element made from a file with the given name.

        :param filename: The name of the file to load.
        """
        root: ElementTree = parse((filename))
        e: Element = root.getroot()
        return self.build(None, e)

    def parser(self, tag: str) -> Callable[[ParserType], ParserType]:
        """Add a new parser to this builder.

        Parsers work on the name on a tag. So if you wish to work on the XML
        ``<title>Hello, title</title>``, you need a parser that knows how to
        handle the ``title`` tag.

        :param tag: The tag name this parser will handle.
        """

        def inner(func: ParserType) -> ParserType:
            """Add ``func`` to the :attr:`~Builder.parsers` dictionary.

            :param func: The function to add.
            """
            self.add_parser(tag, func)
            return func

        return inner

    def add_parser(self, tag: str, func: ParserType) -> None:
        """Add a parser to this builder.

        :param tag: The name of the tag that this parser knows how to handle.

        :param func: The function which will do the actual parsing.
        """
        self.parsers[tag] = func

    def add_builder(self, tag: str, builder: 'Builder') -> None:
        """Add a sub builder to this builder.

        In the same way that parsers know how to handle a single tag, sub
        builders can handle many tags recursively.

        :param tag: The name of the top level tag this sub builder knows how to
            handle.

        :param builder: The builder to add.
        """
        self.builders[tag] = builder
