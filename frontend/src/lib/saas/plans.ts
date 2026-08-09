export type Plan = {
  id: string;
  name: string;
  nameAr: string;
  price: string;
  priceAr: string;
  features: string[];
};

export const PLANS: Plan[] = [
  {
    id: "starter",
    name: "Starter",
    nameAr: "المبتدئ",
    price: "Free",
    priceAr: "مجاني",
    features: [
      "1 chatbot",
      "100 conversations/month",
      "Basic knowledge base",
      "Email support",
    ],
  },
  {
    id: "pro",
    name: "Pro",
    nameAr: "الاحترافي",
    price: "$49/month",
    priceAr: "٤٩$ / شهرياً",
    features: [
      "5 chatbots",
      "Unlimited conversations",
      "Advanced knowledge base",
      "Priority support",
      "Custom branding",
      "Analytics dashboard",
    ],
  },
];
