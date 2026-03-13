from pydantic import BaseModel, Field

class PersonImpression(BaseModel):
    """A single impression of a person from a conversation."""
    person_id: str = Field(description="The person's id from the provided list.")
    impression: str = Field(description="What I noticed.")

class PeopleReflection(BaseModel):
    """My impressions of people from a conversation."""
    impressions: list[PersonImpression] = Field(description="One entry per person I noticed something about. Empty if I learned nothing new.")
