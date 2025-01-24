# src/models.py

from pydantic import BaseModel, Field, HttpUrl, RootModel
from typing import List, Optional, Union


# Search queries response format
class SearchQuery(BaseModel):
    section: str = Field(..., description="The section of the outline the query corresponds to.")
    query: str = Field(..., description="The search query for this section.")


class SearchQueryList(BaseModel):
    """
    Wrapper class for a list of SearchQuery objects.
    """
    root: List[SearchQuery] = Field(..., description="List of search queries.")

class ReferenceItem(BaseModel):
    reference_number: int = Field(..., description="Sequential reference number.")
    authors: Optional[str] = Field(None, description="Author(s) of the reference.")
    year: Optional[Union[int, str]] = Field(None, description="Publication year.")
    title: Optional[str] = Field(None, description="Title of the reference.")
    journal_source: Optional[str] = Field(None, description="Journal or source of publication.")
    url_doi: Optional[str] = Field(None, description="URL or DOI of the reference.")


class FAQItem(BaseModel):
    question: str = Field(..., description="A frequently asked question about the condition.")
    answer: str = Field(..., description="A concise and informative answer to the question.")


# Define all section classes without using Union
class OverviewSection(BaseModel):
    heading: str = Field(default="Overview", description="Heading of the section.")
    content: str = Field(..., description="A high-level introduction to the topic, explaining its significance and impact, key statistics, and facts.")


class KeyFactsSection(BaseModel):
    heading: str = Field(default="Key Facts", description="Heading of the section.")
    content: List[str] = Field(..., description="Notable statistics or key data, presented as a list of strings.")


class SymptomsSection(BaseModel):
    heading: str = Field(default="Symptoms", description="Heading of the section.")
    content: List[str] = Field(..., description="Common signs and symptoms, presented as a list of strings.")


class TypesSection(BaseModel):
    heading: str = Field(default="Types", description="Heading of the section.")
    content: str = Field(..., description="Classifications or subtypes, each with a brief explanation. Types and subtypes may use nested subheadings (###, ####).")


class CausesSection(BaseModel):
    heading: str = Field(default="Causes", description="Heading of the section.")
    content: str = Field(..., description="Explanation of underlying mechanisms or causes, including primary causes.")


class RiskFactorsSection(BaseModel):
    heading: str = Field(default="Risk Factors", description="Heading of the section.")
    content: List[str] = Field(..., description="Factors that increase susceptibility, including lifestyle, genetic, or environmental risk factors.")


class DiagnosisSection(BaseModel):
    heading: str = Field(default="Diagnosis", description="Heading of the section.")
    content: str = Field(..., description="Outline of the diagnostic process, including medical history, clinical symptoms, tests, or imaging tools. Can include subheadings (###) for specific methods.")


class PreventionSection(BaseModel):
    heading: str = Field(default="Prevention", description="Heading of the section.")
    content: List[str] = Field(..., description="Practical advice for risk reduction, with evidence-based recommendations.")


class SpecialistToVisitSection(BaseModel):
    heading: str = Field(default="Specialist to Visit", description="Heading of the section.")
    content: str = Field(..., description="Healthcare providers involved in diagnosis and treatment, and their roles.")


class TreatmentSection(BaseModel):
    heading: str = Field(default="Treatment", description="Heading of the section.")
    content: str = Field(..., description="Description of medical and therapeutic interventions.")


class HomeCareSection(BaseModel):
    heading: str = Field(default="Home-Care", description="Heading of the section.")
    content: List[str] = Field(..., description="Tips for self-management, such as lifestyle adjustments, routines, or home remedies.")


class LivingWithSection(BaseModel):
    heading: str = Field(default="Living With", description="Heading of the section.")
    content: str = Field(..., description="Guidance for long-term management, including emotional, social, or physical adaptation strategies.")


class ComplicationsSection(BaseModel):
    heading: str = Field(default="Complications", description="Heading of the section.")
    content: str = Field(..., description="Discussion of potential health challenges if the condition is untreated or poorly managed.")


class AlternativeTherapiesSection(BaseModel):
    heading: str = Field(default="Alternative Therapies", description="Heading of the section.")
    content: str = Field(..., description="Summary of non-conventional approaches.")


class FAQsSection(BaseModel):
    heading: str = Field(default="FAQs", description="Heading of the section.")
    content: List[FAQItem] = Field(..., description="A list of frequently asked questions and their corresponding answers.")


class ReferencesSection(BaseModel):
    heading: str = Field(default="References", description="Heading of the section.")
    content: List[ReferenceItem] = Field(..., description="A list of references.")


class Article(BaseModel):
    title: str = Field(..., description="The main heading of the article.")
    subtitle: str = Field(..., description="A concise introductory phrase summarizing the condition.")
    
    overview: OverviewSection = Field(..., description="Overview section of the article.")
    key_facts: KeyFactsSection = Field(..., description="Key Facts section of the article.")
    symptoms: SymptomsSection = Field(..., description="Symptoms section of the article.")
    types: TypesSection = Field(..., description="Types section of the article.")
    causes: CausesSection = Field(..., description="Causes section of the article.")
    risk_factors: RiskFactorsSection = Field(..., description="Risk Factors section of the article.")
    diagnosis: DiagnosisSection = Field(..., description="Diagnosis section of the article.")
    prevention: PreventionSection = Field(..., description="Prevention section of the article.")
    specialist_to_visit: SpecialistToVisitSection = Field(..., description="Specialist to Visit section of the article.")
    treatment: TreatmentSection = Field(..., description="Treatment section of the article.")
    home_care: HomeCareSection = Field(..., description="Home-Care section of the article.")
    living_with: LivingWithSection = Field(..., description="Living With section of the article.")
    complications: ComplicationsSection = Field(..., description="Complications section of the article.")
    alternative_therapies: AlternativeTherapiesSection = Field(..., description="Alternative Therapies section of the article.")
    faqs: FAQsSection = Field(..., description="FAQs section of the article.")
    references: ReferencesSection = Field(..., description="References section of the article.")


class Author(BaseModel):
    name: str

class PublicationVenue(BaseModel):
    name: Optional[str] = None
    SJR: Optional[float] = None

class ExternalIds(BaseModel):
    DOI: Optional[str] = None

class Paper(BaseModel):
    section: str
    query: str
    title: str
    abstract: str
    authors: List[Author] = []
    citationCount: Optional[int] = None
    referenceCount: Optional[int] = None
    url: Optional[HttpUrl] = None
    venue: Optional[str] = None
    # publicationVenue: Optional[PublicationVenue] = None
    year: Optional[Union[int, str]] = None 
    openAccessPdf: Optional[HttpUrl] = None
    externalIds: Optional[ExternalIds] = None
    citation: str = Field(..., description="APA-like citation with author(s), title, year, source, DOI/URL")
