import { Skill } from "@/lib/api";

interface SkillLibraryProps {
  skills: Skill[];
}

// 分类颜色映射
const categoryColors: Record<string, { bg: string; text: string; gradient: string }> = {
  "equipment-fault": { bg: "bg-red-50", text: "text-red-700", gradient: "from-red-400 to-rose-500" },
  "refund-cancellation": { bg: "bg-orange-50", text: "text-orange-700", gradient: "from-orange-400 to-amber-500" },
  "price-inquiry": { bg: "bg-emerald-50", text: "text-emerald-700", gradient: "from-emerald-400 to-teal-500" },
  "technical-support": { bg: "bg-blue-50", text: "text-blue-700", gradient: "from-blue-400 to-indigo-500" },
  "logistics-issue": { bg: "bg-purple-50", text: "text-purple-700", gradient: "from-purple-400 to-violet-500" },
  "complaint-suggestion": { bg: "bg-pink-50", text: "text-pink-700", gradient: "from-pink-400 to-rose-500" },
  "other": { bg: "bg-gray-50", text: "text-gray-700", gradient: "from-gray-400 to-slate-500" },
};

const getCategoryStyle = (category: string) => {
  return categoryColors[category] || categoryColors["other"];
};

export default function SkillLibrary({ skills }: SkillLibraryProps) {
  // Group skills by category
  const byCategory = skills.reduce((acc, skill) => {
    if (!acc[skill.category]) {
      acc[skill.category] = [];
    }
    acc[skill.category].push(skill);
    return acc;
  }, {} as Record<string, Skill[]>);

  const totalUsage = skills.reduce((sum, s) => sum + s.usage_count, 0);

  return (
    <div className="w-72 liquid-glass-panel border-l border-white/30 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200/50 bg-gradient-to-r from-white to-gray-50/50">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-md">
            <span className="text-white text-lg">💡</span>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Skill Library</h3>
            <p className="text-xs text-gray-500">{skills.length} skills loaded</p>
          </div>
        </div>
        
        {/* Stats */}
        {skills.length > 0 && (
          <div className="flex gap-2">
            <div className="flex-1 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-lg p-2.5 border border-indigo-100">
              <p className="text-xs text-indigo-600 font-medium">Categories</p>
              <p className="text-lg font-bold text-indigo-700">{Object.keys(byCategory).length}</p>
            </div>
            <div className="flex-1 bg-gradient-to-br from-emerald-50 to-teal-50 rounded-lg p-2.5 border border-emerald-100">
              <p className="text-xs text-emerald-600 font-medium">Total Uses</p>
              <p className="text-lg font-bold text-emerald-700">{totalUsage}</p>
            </div>
          </div>
        )}
      </div>

      {/* Skills List */}
      <div className="flex-1 overflow-y-auto p-3">
        {skills.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
              <span className="text-2xl">📚</span>
            </div>
            <p className="text-sm text-gray-500 font-medium mb-1">No skills yet</p>
            <p className="text-xs text-gray-400">
              Sync emails and run learning<br />to generate skills
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(byCategory).map(([category, categorySkills]) => {
              const style = getCategoryStyle(category);
              return (
                <div key={category} className="animate-fadeInUp">
                  {/* Category Header */}
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${style.gradient}`}></div>
                    <h4 className={`text-xs font-semibold uppercase tracking-wider ${style.text}`}>
                      {category.replace(/-/g, " ")}
                    </h4>
                    <span className="text-xs text-gray-400">({categorySkills.length})</span>
                  </div>
                  
                  {/* Skills */}
                  <div className="space-y-2">
                    {categorySkills.map((skill) => (
                      <div
                        key={skill.id}
                        className={`group p-3 liquid-glass-card rounded-xl hover-lift cursor-pointer`}
                      >
                        <p className="text-sm font-medium text-gray-900 mb-1.5 group-hover:text-indigo-700 transition-colors">
                          {skill.name}
                        </p>
                        
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-500">
                            {skill.trigger_keywords.length} keywords
                          </span>
                          <div className="flex items-center gap-1.5">
                            <div className={`w-1.5 h-1.5 rounded-full bg-gradient-to-r ${style.gradient}`}></div>
                            <span className={style.text}>{skill.usage_count} uses</span>
                          </div>
                        </div>
                        
                        {/* Usage Progress Bar */}
                        {totalUsage > 0 && (
                          <div className="mt-2 h-1 bg-gray-200 rounded-full overflow-hidden">
                            <div 
                              className={`h-full bg-gradient-to-r ${style.gradient} transition-all duration-500`}
                              style={{ width: `${Math.max((skill.usage_count / totalUsage) * 100, 5)}%` }}
                            ></div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
