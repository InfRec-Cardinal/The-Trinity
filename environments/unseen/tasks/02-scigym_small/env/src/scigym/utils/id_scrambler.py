from collections import defaultdict
from typing import Dict, List, Set

import libsbml

from scigym.utils.main import generate_new_id


class SIdScrambler(libsbml.IdentifierTransformer):
    real_to_fake_ids: Dict[int, Dict[str, str]]

    def __init__(
        self,
        ids: List[str],
        type_codes_to_ignore: List[int] = [libsbml.SBML_LOCAL_PARAMETER],
    ):
        libsbml.IdentifierTransformer.__init__(self)
        self.touched_ids: Set[str] = set()
        self.existingIds: List[str] = ids
        self.real_to_fake_ids = defaultdict(dict)
        self.type_codes_to_ignore = type_codes_to_ignore

    def transform(self, element: libsbml.SBase):
        type_code = element.getTypeCode()
        mid = element.getMetaId()
        oldId = element.getId()
        isSetIdAttribute = element.isSetIdAttribute()

        if element is None or type_code in self.type_codes_to_ignore or mid in self.touched_ids:
            return libsbml.LIBSBML_OPERATION_SUCCESS

        if not isSetIdAttribute or oldId is None or oldId == "":
            return libsbml.LIBSBML_OPERATION_SUCCESS

        assert oldId not in self.real_to_fake_ids[type_code].keys()
        newId = generate_new_id(ban_list=self.existingIds)

        assert libsbml.SyntaxChecker.isValidInternalSId(newId)
        assert newId not in self.existingIds
        assert newId not in self.real_to_fake_ids[type_code].values()

        element.setId(newId)
        self.touched_ids.add(mid)
        self.real_to_fake_ids[type_code][oldId] = newId
        self.existingIds.append(newId)
        return libsbml.LIBSBML_OPERATION_SUCCESS
