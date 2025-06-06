import { useTranslate } from '@/hooks/common-hooks';
import { Form, Slider } from 'antd';
import { useFormContext } from 'react-hook-form';
import { SingleFormSlider } from './ui/dual-range-slider';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from './ui/form';

type FieldType = {
  top_n?: number;
};

interface IProps {
  initialValue?: number;
  max?: number;
}

const TopNItem = ({ initialValue = 8, max = 100 }: IProps) => {
  const { t } = useTranslate('chat');

  return (
    <Form.Item<FieldType>
      label={t('topN')}
      name={'top_n'}
      initialValue={initialValue}
      tooltip={t('topNTip')}
    >
      <Slider max={max} />
    </Form.Item>
  );
};

export default TopNItem;

interface SimilaritySliderFormFieldProps {
  max?: number;
}

export function TopNFormField({ max = 30 }: SimilaritySliderFormFieldProps) {
  const form = useFormContext();
  const { t } = useTranslate('chat');

  return (
    <FormField
      control={form.control}
      name={'top_n'}
      render={({ field }) => (
        <FormItem>
          <FormLabel tooltip={t('topNTip')}>{t('topN')}</FormLabel>
          <FormControl>
            <SingleFormSlider {...field} max={max}></SingleFormSlider>
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
