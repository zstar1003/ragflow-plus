import ListFilterBar from '@/components/list-filter-bar';
import { Plus } from 'lucide-react';

export default function SearchList() {
  return (
    <section>
      <div className="px-8 pt-8">
        <ListFilterBar title="Search apps">
          <Plus className="mr-2 h-4 w-4" />
          Create app
        </ListFilterBar>
      </div>
      <div className="grid gap-6 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8 max-h-[84vh] overflow-auto px-8"></div>
    </section>
  );
}
