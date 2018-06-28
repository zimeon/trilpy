"""Utilities supporting LDP rules."""
from .namespace import LDP

LDPR_URI = str(LDP.Resource)
LDPNR_URI = str(LDP.NonRDFSource)
LDPRS_URI = str(LDP.RDFSource)
LDPC_URI = str(LDP.Container)
LDPBC_URI = str(LDP.BasicContainer)
LDPDC_URI = str(LDP.DirectContainer)
LDPIC_URI = str(LDP.IndirectContainer)

# Note that LDP_CONTAINER_TYPE_URIS includes only specific container
# types and not the generic LDPC_URI
LDP_CONTAINER_TYPE_URIS = (LDPBC_URI, LDPDC_URI, LDPIC_URI)


def is_ldp_same_or_sub_type(new_type, current_type):
    """True if new_type URI is the same or a sub-type of current_type URI."""
    if new_type == current_type:
        return True
    elif current_type in (LDPNR_URI, LDPBC_URI, LDPDC_URI, LDPIC_URI):
        return False  # no sub-types
    elif current_type == LDPC_URI:
        return new_type in (LDPBC_URI, LDPDC_URI, LDPIC_URI)
    elif current_type == LDPRS_URI:
        return new_type in (LDPC_URI, LDPBC_URI, LDPDC_URI, LDPIC_URI)
    else:
        return False
