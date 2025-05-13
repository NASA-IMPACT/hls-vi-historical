<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output omit-xml-declaration="yes" indent="yes" encoding="utf-8" />

    <!-- Identity transform: copy all elements, attributes, and text -->
    <xsl:template match="node()|@*">
        <xsl:copy>
            <xsl:apply-templates select="node()|@*" />
        </xsl:copy>
    </xsl:template>

    <!--
    Do nothing for these matches (i.e., do NOT copy them over) because their values
    are specific to the HLS files, and don't make sense for the HLS VI files.  Cumulus
    ingestion will appropriately re-populate these for us.

    NOTE: In theory, we could eliminate the parent elements of ProviderBrowseUrl,
    OnlineAccessURL, and OnlineResource, but the HLS VI code that generates the CMR
    XML metadata assumes that at least an empty OnlineAccessURLs parent element exists,
    so we need to keep an empty parent element rather than completely removing it.
    Otherwise, the "generate metadata" step will blow up.
    -->

    <xsl:template match="AdditionalFile" />
    <xsl:template match="ProviderBrowseUrl" />
    <xsl:template match="OnlineAccessURL" />
    <xsl:template match="OnlineResource" />

    <!-- Strip resulting whitespace from the parent elements from which the above
    elements were removed, just to tidy things up. -->
    <!-- Hopefully this won't cause a problem as noted in
    https://lxml.de/xpathxslt.html#xslt, since we are not using elements="*". -->

    <xsl:strip-space
        elements="DataGranule AssociatedBrowseImageUrls OnlineAccessURLs OnlineResources" />
</xsl:stylesheet>
